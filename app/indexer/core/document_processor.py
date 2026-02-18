"""
Document processor for the Policy Indexer pipeline.

Orchestrates the full processing flow for a single PDF document:
  Download → OCR (Document Intelligence) → Chunk → Embed → Push to AI Search index.

This replaces the AI Search skillset pipeline (OcrSkill + SplitSkill +
AzureOpenAIEmbeddingSkill) with in-app processing that works in private
networking scenarios.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.storage.blob import BlobServiceClient

from .chunker import Chunk, ChunkerConfig, TextChunker
from .embedder import Embedder, EmbedderConfig
from .session_tracker import SessionTracker, StepStatus

logger = logging.getLogger("policy-indexer")


def _get_azure_credential() -> DefaultAzureCredential:
    """Build a DefaultAzureCredential that targets the user-assigned managed identity when available."""
    client_id = os.environ.get("AZURE_CLIENT_ID")
    if client_id:
        return DefaultAzureCredential(managed_identity_client_id=client_id)
    return DefaultAzureCredential()


@dataclass
class ProcessingResult:
    """Result of processing a single document."""

    session_id: str
    blob_name: str
    page_count: int = 0
    chunk_count: int = 0
    success: bool = True
    error: Optional[str] = None
    duration_seconds: float = 0.0


class DocumentProcessor:
    """
    Processes a single PDF: OCR → chunk → embed → push to AI Search index.

    All external calls (Document Intelligence, Azure OpenAI, AI Search, Blob Storage)
    go through private endpoints when the Function App has VNet integration.
    """

    def __init__(
        self,
        chunker_config: Optional[ChunkerConfig] = None,
        embedder_config: Optional[EmbedderConfig] = None,
        index_name: Optional[str] = None,
        blob_container_name: Optional[str] = None,
    ):
        # --- Blob Storage (RBAC-first) ---
        self.blob_container_name = blob_container_name or os.environ.get(
            "AZURE_BLOB_CONTAINER_NAME",
            os.environ.get("AZURE_STORAGE_BLOB_CONTAINER_NAME", "pre-auth-policies"),
        )
        storage_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "")
        storage_conn = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")

        if storage_account:
            # Prefer managed-identity / Entra ID auth
            account_url = f"https://{storage_account}.blob.core.windows.net"
            self.blob_service_client = BlobServiceClient(
                account_url=account_url, credential=_get_azure_credential()
            )
            logger.info(
                "BlobServiceClient using managed-identity auth for '%s'",
                storage_account,
            )
        elif storage_conn:
            # Fallback: connection string (local development)
            self.blob_service_client = BlobServiceClient.from_connection_string(
                storage_conn
            )
            logger.info("BlobServiceClient using connection-string auth")
        else:
            raise EnvironmentError(
                "Set AZURE_STORAGE_ACCOUNT_NAME (preferred) or AZURE_STORAGE_CONNECTION_STRING"
            )

        # --- Document Intelligence (OCR, RBAC-first) ---
        di_endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        di_key = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        if not di_key:
            # Prefer managed-identity / Entra ID auth
            self.doc_intelligence_client = DocumentIntelligenceClient(
                endpoint=di_endpoint,
                credential=_get_azure_credential(),
                api_version="2024-11-30",
            )
            logger.info("DocumentIntelligence using managed-identity auth")
        else:
            # Fallback: API key (local development)
            self.doc_intelligence_client = DocumentIntelligenceClient(
                endpoint=di_endpoint,
                credential=AzureKeyCredential(di_key),
                api_version="2024-11-30",
            )
            logger.info("DocumentIntelligence using API key auth")

        # --- Chunker & Embedder ---
        self.chunker = TextChunker(config=chunker_config)
        self.embedder = Embedder(config=embedder_config)

        # --- AI Search (push, RBAC-first) ---
        search_endpoint = os.environ.get("AZURE_AI_SEARCH_SERVICE_ENDPOINT", "")
        search_key = os.environ.get("AZURE_AI_SEARCH_ADMIN_KEY")
        self.index_name = index_name or os.environ.get(
            "AZURE_SEARCH_INDEX_NAME", "ai-policies-index"
        )

        if not search_key:
            # Prefer managed-identity / Entra ID auth
            search_credential = _get_azure_credential()
            logger.info("SearchClient using managed-identity auth")
        else:
            # Fallback: admin key (local development)
            search_credential = AzureKeyCredential(search_key)
            logger.info("SearchClient using admin key auth")

        self.search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=self.index_name,
            credential=search_credential,
        )

        # --- Session tracker ---
        self.session_tracker = SessionTracker()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def process(
        self, blob_name: str, blob_url: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a single PDF blob end-to-end.

        Args:
            blob_name: The blob path within the container (e.g. ``policies_ocr/policy.pdf``).
            blob_url: Optional full blob URL (for logging).

        Returns:
            ProcessingResult with session details.
        """
        session = self.session_tracker.create_session(blob_name)
        start_time = time.time()

        try:
            # Step 1: Download PDF
            session.update_step("download", StepStatus.RUNNING)
            pdf_bytes = self._download_blob(blob_name)
            session.update_step(
                "download", StepStatus.COMPLETED, detail=f"{len(pdf_bytes)} bytes"
            )

            # Step 2: OCR via Document Intelligence
            session.update_step("ocr", StepStatus.RUNNING)
            pages = self._run_ocr(pdf_bytes)
            session.update_step(
                "ocr", StepStatus.COMPLETED, detail=f"{len(pages)} pages"
            )

            # Step 3: Chunk
            session.update_step("chunking", StepStatus.RUNNING)
            chunks = self.chunker.chunk_pages(pages)
            session.update_step(
                "chunking", StepStatus.COMPLETED, detail=f"{len(chunks)} chunks"
            )

            if not chunks:
                logger.warning("No chunks produced for %s — empty document?", blob_name)
                session.complete(
                    success=True, detail="No chunks produced (empty document)"
                )
                return ProcessingResult(
                    session_id=session.session_id,
                    blob_name=blob_name,
                    page_count=len(pages),
                    chunk_count=0,
                    duration_seconds=time.time() - start_time,
                )

            # Step 4: Embed
            session.update_step("embedding", StepStatus.RUNNING)
            chunk_texts = [c.text for c in chunks]
            embeddings = self.embedder.embed_texts(chunk_texts)
            session.update_step(
                "embedding", StepStatus.COMPLETED, detail=f"{len(embeddings)} vectors"
            )

            # Step 5: Build index documents and push
            session.update_step("indexing", StepStatus.RUNNING)
            documents = self._build_index_documents(chunks, embeddings, blob_name)
            self._push_to_index(documents)
            session.update_step(
                "indexing", StepStatus.COMPLETED, detail=f"{len(documents)} docs pushed"
            )

            duration = time.time() - start_time
            session.complete(success=True, detail=f"Completed in {duration:.1f}s")

            logger.info(
                "Processed %s: %d pages, %d chunks, %.1fs",
                blob_name,
                len(pages),
                len(chunks),
                duration,
            )

            return ProcessingResult(
                session_id=session.session_id,
                blob_name=blob_name,
                page_count=len(pages),
                chunk_count=len(chunks),
                duration_seconds=duration,
            )

        except Exception as exc:
            duration = time.time() - start_time
            error_msg = f"{type(exc).__name__}: {exc}"
            session.complete(success=False, detail=error_msg)

            logger.exception("Failed to process %s after %.1fs", blob_name, duration)

            return ProcessingResult(
                session_id=session.session_id,
                blob_name=blob_name,
                success=False,
                error=error_msg,
                duration_seconds=duration,
            )

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------
    def _download_blob(self, blob_name: str) -> bytes:
        """Download a blob from the configured container."""
        container_client = self.blob_service_client.get_container_client(
            self.blob_container_name
        )
        blob_client = container_client.get_blob_client(blob_name)
        data = blob_client.download_blob().readall()
        logger.info("Downloaded %s (%d bytes)", blob_name, len(data))
        return data

    def _run_ocr(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Run Document Intelligence OCR (prebuilt-layout) on PDF bytes.

        Returns a list of page dicts: [{text: str, page_number: int}, ...]
        """
        poller = self.doc_intelligence_client.begin_analyze_document(
            model_id="prebuilt-layout",
            body=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
            output_content_format="text",
        )
        result = poller.result()

        pages: List[Dict[str, Any]] = []

        if result.pages:
            for page in result.pages:
                page_num = (
                    page.page_number if hasattr(page, "page_number") else len(pages) + 1
                )

                # Collect text from lines on this page
                page_lines = []
                if page.lines:
                    for line in page.lines:
                        page_lines.append(line.content)

                page_text = "\n".join(page_lines) if page_lines else ""

                pages.append(
                    {
                        "text": page_text,
                        "page_number": page_num,
                    }
                )
        elif result.content:
            # Fallback: if pages aren't structured, use full content
            pages.append({"text": result.content, "page_number": 1})

        logger.info("OCR extracted %d pages", len(pages))
        return pages

    def _build_index_documents(
        self,
        chunks: List[Chunk],
        embeddings: List[List[float]],
        blob_name: str,
    ) -> List[Dict[str, Any]]:
        """Build AI Search index document dicts from chunks + embeddings."""
        parent_id = TextChunker.generate_parent_id(blob_name)
        title = os.path.basename(blob_name)

        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = TextChunker.generate_chunk_id(blob_name, chunk.index)
            doc = {
                "chunk_id": chunk_id,
                "chunk": chunk.text,
                "vector": embedding,
                "parent_id": parent_id,
                "title": title,
                "parent_path": blob_name,
                "page_number": chunk.page_number or "",
            }
            documents.append(doc)

        return documents

    def _push_to_index(self, documents: List[Dict[str, Any]]) -> None:
        """Push documents to the AI Search index using merge-or-upload (upsert)."""
        # AI Search SDK supports up to 1000 documents per batch
        batch_size = 1000
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            result = self.search_client.merge_or_upload_documents(batch)  # type: ignore[arg-type]

            succeeded = sum(1 for r in result if r.succeeded)
            failed = sum(1 for r in result if not r.succeeded)

            if failed:
                errors = [
                    f"{r.key}: {r.error_message}" for r in result if not r.succeeded
                ]
                logger.error(
                    "Index push: %d succeeded, %d failed. Errors: %s",
                    succeeded,
                    failed,
                    errors[:5],
                )
                raise RuntimeError(f"Failed to index {failed} documents: {errors[:3]}")

            logger.info("Pushed %d documents to index", succeeded)

    # ------------------------------------------------------------------
    # Utility: list all blobs for reindex
    # ------------------------------------------------------------------
    def list_blobs(self, prefix: str = "policies_ocr/") -> List[str]:
        """List all PDF blobs in the container under the given prefix."""
        container_client = self.blob_service_client.get_container_client(
            self.blob_container_name
        )
        blobs = container_client.list_blobs(name_starts_with=prefix)
        return [b.name for b in blobs if b.name.lower().endswith(".pdf")]
