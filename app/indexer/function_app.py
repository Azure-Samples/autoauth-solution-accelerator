"""
Policy Indexer — Azure Function App (v2 programming model)

Blob-triggered document processing pipeline that replaces the AI Search
skillset/indexer/data-source architecture.  All document processing (OCR,
chunking, embedding) happens inside the Function App, and fully-formed
documents are pushed directly to the AI Search index.

Endpoints:
  EventGrid  process_blob          — Auto-triggered on blob created events
  POST /api/process_blob_manual    — Manually (re)process a specific blob
  POST /api/reindex_all            — Reprocess every PDF in the container
  POST /api/setup_index            — Create/update AI Search index schema
  POST /api/upload_policies        — Upload PDF files to blob storage
  POST /api/vectorize              — Pre-vectorize query text (for search plugin)
  GET  /api/processing_status      — Session-level processing observability
  GET  /api/health                 — Health check
"""

import json
import logging
import os
from urllib.parse import unquote

import azure.functions as func

from core.document_processor import DocumentProcessor
from core.embedder import Embedder
from core.index_manager import IndexManager
from core.session_tracker import get_global_tracker

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

logger = logging.getLogger("policy-indexer")


def _json_response(body: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(body, default=str),
        status_code=status_code,
        mimetype="application/json",
    )


def _extract_blob_name_from_event(event_data: dict) -> str:
    """Extract the blob path from an Event Grid event payload."""
    url: str = event_data.get("url", "")
    # URL format: https://<account>.blob.core.windows.net/<container>/<blob_path>
    # We need the blob_path portion
    if "/blobs/" in url:
        blob_path = url.split("/blobs/", 1)[1]
    elif url:
        # Fallback: take everything after the container name
        parts = url.split("/")
        # Find container segment and take the rest
        try:
            container_idx = parts.index("pre-auth-policies")
            blob_path = "/".join(parts[container_idx + 1 :])
        except ValueError:
            blob_path = parts[-1]
    else:
        blob_path = event_data.get("subject", "").rsplit("/blobs/", 1)[-1]

    return unquote(blob_path)


# ---------------------------------------------------------------------------
# EventGrid trigger — process_blob
# ---------------------------------------------------------------------------
@app.function_name("process_blob")
@app.event_grid_trigger(arg_name="event")
def process_blob(event: func.EventGridEvent):
    """
    Triggered when a PDF is uploaded/updated in the policies blob container.

    The Event Grid subscription should be configured with:
      - Source: Storage Account
      - Event types: Microsoft.Storage.BlobCreated
      - Subject prefix: /blobServices/default/containers/pre-auth-policies/blobs/policies_ocr/
      - Subject suffix: .pdf
    """
    event_data = event.get_json()
    blob_name = _extract_blob_name_from_event(event_data)

    if not blob_name.lower().endswith(".pdf"):
        logger.info("Skipping non-PDF blob: %s", blob_name)
        return

    logger.info(
        "Event Grid trigger: processing %s (event_type=%s)",
        blob_name,
        event.event_type,
    )

    processor = DocumentProcessor()
    result = processor.process(blob_name=blob_name, blob_url=event_data.get("url"))

    if result.success:
        logger.info(
            "Successfully processed %s: %d chunks (session=%s)",
            blob_name,
            result.chunk_count,
            result.session_id,
        )
    else:
        logger.error(
            "Failed to process %s: %s (session=%s)",
            blob_name,
            result.error,
            result.session_id,
        )


# ---------------------------------------------------------------------------
# POST /api/process_blob_manual
# ---------------------------------------------------------------------------
@app.function_name("process_blob_manual")
@app.route(route="process_blob_manual", methods=["POST"])
def process_blob_manual(req: func.HttpRequest) -> func.HttpResponse:
    """
    Manually (re)process a specific blob.

    Request body: {"blob_name": "policies_ocr/my-policy.pdf"}
    """
    try:
        body = req.get_json()
        blob_name = body.get("blob_name", "")

        if not blob_name:
            return _json_response(
                {"status": "error", "detail": "blob_name is required"}, 400
            )

        processor = DocumentProcessor()
        result = processor.process(blob_name=blob_name)

        return _json_response(
            {
                "status": "ok" if result.success else "error",
                "session_id": result.session_id,
                "blob_name": result.blob_name,
                "page_count": result.page_count,
                "chunk_count": result.chunk_count,
                "duration_seconds": round(result.duration_seconds, 2),
                "error": result.error,
            },
            200 if result.success else 500,
        )
    except Exception as exc:
        logger.exception("process_blob_manual failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/reindex_all
# ---------------------------------------------------------------------------
@app.function_name("reindex_all")
@app.route(route="reindex_all", methods=["POST"])
def reindex_all(req: func.HttpRequest) -> func.HttpResponse:
    """
    Reprocess every PDF in the blob container.

    Optionally accepts: {"prefix": "policies_ocr/"}
    """
    try:
        body = {}
        try:
            body = req.get_json()
        except ValueError:
            pass

        prefix = body.get("prefix", "policies_ocr/")

        processor = DocumentProcessor()
        blobs = processor.list_blobs(prefix=prefix)

        if not blobs:
            return _json_response(
                {"status": "ok", "detail": "No PDF blobs found", "blobs": []}, 200
            )

        results = []
        for blob_name in blobs:
            result = processor.process(blob_name=blob_name)
            results.append(
                {
                    "blob_name": result.blob_name,
                    "session_id": result.session_id,
                    "success": result.success,
                    "chunk_count": result.chunk_count,
                    "error": result.error,
                }
            )

        total = len(results)
        succeeded = sum(1 for r in results if r["success"])
        failed = total - succeeded

        return _json_response(
            {
                "status": "ok" if failed == 0 else "partial",
                "total": total,
                "succeeded": succeeded,
                "failed": failed,
                "results": results,
            },
            200 if failed == 0 else 207,
        )
    except Exception as exc:
        logger.exception("reindex_all failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/setup_index
# ---------------------------------------------------------------------------
@app.function_name("setup_index")
@app.route(route="setup_index", methods=["POST"])
def setup_index(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create or update the AI Search index schema.

    This only creates the index — no skillsets, indexers, or data sources.
    Idempotent — safe to call repeatedly.
    """
    try:
        manager = IndexManager()
        result = manager.setup_all()
        return _json_response({"status": "ok", "resources": result})
    except Exception as exc:
        logger.exception("setup_index failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/upload_policies
# ---------------------------------------------------------------------------
@app.function_name("upload_policies")
@app.route(route="upload_policies", methods=["POST"])
def upload_policies(req: func.HttpRequest) -> func.HttpResponse:
    """
    Upload PDF policy documents to blob storage and optionally process them
    synchronously (OCR → chunk → embed → push to index).

    Query parameters:
      - process: Set to ``true`` to process immediately after upload rather
        than waiting for the Event Grid trigger.  Defaults to ``false``.

    Accepts either:
      - multipart/form-data with one or more PDF file fields
      - application/octet-stream with ``X-Filename`` header
    """
    try:
        processor = DocumentProcessor()
        uploaded = []

        content_type = req.headers.get("Content-Type", "")
        container_client = processor.blob_service_client.get_container_client(
            processor.blob_container_name
        )
        remote_path = "policies_ocr"

        if "multipart/form-data" in content_type:
            for name, file in req.files.items():
                filename = file.filename or name
                if not filename.lower().endswith(".pdf"):
                    continue
                blob_path = f"{remote_path}/{filename}"
                blob_client = container_client.get_blob_client(blob_path)
                blob_client.upload_blob(file.read(), overwrite=True)
                uploaded.append(blob_path)
        else:
            filename = req.headers.get("X-Filename", "upload.pdf")
            body = req.get_body()
            if not body:
                return _json_response(
                    {"status": "error", "detail": "Empty request body"}, 400
                )
            blob_path = f"{remote_path}/{filename}"
            blob_client = container_client.get_blob_client(blob_path)
            blob_client.upload_blob(body, overwrite=True)
            uploaded.append(blob_path)

        # Synchronous processing when ?process=true
        process_now = req.params.get("process", "false").lower() == "true"
        processing_results = []

        if process_now and uploaded:
            for blob_path in uploaded:
                result = processor.process(blob_name=blob_path)
                processing_results.append(
                    {
                        "blob_name": result.blob_name,
                        "session_id": result.session_id,
                        "success": result.success,
                        "page_count": result.page_count,
                        "chunk_count": result.chunk_count,
                        "duration_seconds": round(result.duration_seconds, 2),
                        "error": result.error,
                    }
                )

            total = len(processing_results)
            succeeded = sum(1 for r in processing_results if r["success"])
            failed = total - succeeded

            return _json_response(
                {
                    "status": "ok" if failed == 0 else "partial",
                    "uploaded_count": len(uploaded),
                    "blobs": uploaded,
                    "processing": {
                        "total": total,
                        "succeeded": succeeded,
                        "failed": failed,
                        "results": processing_results,
                    },
                },
                200 if failed == 0 else 207,
            )

        return _json_response(
            {
                "status": "ok",
                "uploaded_count": len(uploaded),
                "blobs": uploaded,
                "note": "Processing will be triggered automatically via Event Grid",
            }
        )
    except Exception as exc:
        logger.exception("upload_policies failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# POST /api/vectorize
# ---------------------------------------------------------------------------
@app.function_name("vectorize")
@app.route(route="vectorize", methods=["POST"])
def vectorize(req: func.HttpRequest) -> func.HttpResponse:
    """
    Pre-vectorize query text using Azure OpenAI embeddings.

    This endpoint allows the search plugin (or any client) to obtain
    embedding vectors without relying on the AI Search vectorizer,
    eliminating the need for AI Search → OpenAI outbound connectivity.

    Request body: {"text": "query text here"}
    Or for batch:  {"texts": ["query 1", "query 2"]}
    """
    try:
        body = req.get_json()
        text = body.get("text")
        texts = body.get("texts")

        if not text and not texts:
            return _json_response(
                {"status": "error", "detail": "Provide 'text' or 'texts'"}, 400
            )

        embedder = Embedder()

        if text and not texts:
            vector = embedder.embed_single(text)
            return _json_response(
                {"status": "ok", "vector": vector, "dimensions": len(vector)}
            )

        if texts:
            vectors = embedder.embed_texts(texts)
            return _json_response(
                {
                    "status": "ok",
                    "vectors": vectors,
                    "count": len(vectors),
                    "dimensions": len(vectors[0]) if vectors else 0,
                }
            )

    except Exception as exc:
        logger.exception("vectorize failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# GET /api/processing_status
# ---------------------------------------------------------------------------
@app.function_name("processing_status")
@app.route(route="processing_status", methods=["GET"])
def processing_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    Return processing session details for observability.

    Query parameters:
      - session_id: Get details for a specific session
      - blob_name:  Get all sessions for a specific blob
      - filter:     "failed" to show only failures, "recent" for recent (default)
      - limit:      Max results (default 50)
      (no params):  Returns summary + recent sessions
    """
    try:
        tracker = get_global_tracker()
        session_id = req.params.get("session_id")
        blob_name = req.params.get("blob_name")
        filter_type = req.params.get("filter", "recent")
        limit = int(req.params.get("limit", "50"))

        # Specific session lookup
        if session_id:
            session = tracker.get_session(session_id)
            if not session:
                return _json_response(
                    {"status": "not_found", "session_id": session_id}, 404
                )
            return _json_response({"status": "ok", "session": session.to_dict()})

        # Sessions by blob name
        if blob_name:
            sessions = tracker.get_sessions_by_blob(blob_name)
            return _json_response(
                {
                    "status": "ok",
                    "blob_name": blob_name,
                    "count": len(sessions),
                    "sessions": [s.to_dict() for s in sessions[-limit:]],
                }
            )

        # Failed sessions
        if filter_type == "failed":
            sessions = tracker.list_failed(limit=limit)
            return _json_response(
                {
                    "status": "ok",
                    "filter": "failed",
                    "count": len(sessions),
                    "sessions": [s.to_dict() for s in sessions],
                }
            )

        # Default: summary + recent
        summary = tracker.get_summary()
        recent = tracker.list_recent(limit=limit)
        return _json_response(
            {
                "status": "ok",
                "summary": summary,
                "recent_sessions": [s.to_dict() for s in recent],
            }
        )

    except Exception as exc:
        logger.exception("processing_status failed")
        return _json_response({"status": "error", "detail": str(exc)}, 500)


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------
@app.function_name("health")
@app.route(route="health", methods=["GET"])
def health(req: func.HttpRequest) -> func.HttpResponse:
    """Health check — validates connectivity to AI Search, Blob Storage, OpenAI, and Document Intelligence."""
    checks = {}

    # AI Search
    try:
        manager = IndexManager()
        manager.index_client.get_service_statistics()
        checks["ai_search"] = "ok"
    except Exception as exc:
        checks["ai_search"] = f"error: {exc}"

    # Blob Storage
    try:
        processor = DocumentProcessor()
        processor.blob_service_client.get_service_properties()
        checks["blob_storage"] = "ok"
    except Exception as exc:
        checks["blob_storage"] = f"error: {exc}"

    # Document Intelligence
    try:
        di_endpoint = os.environ.get("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT", "")
        if di_endpoint:
            checks["document_intelligence"] = "configured"
        else:
            checks["document_intelligence"] = "not_configured"
    except Exception as exc:
        checks["document_intelligence"] = f"error: {exc}"

    # Azure OpenAI
    try:
        openai_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        if openai_endpoint:
            checks["azure_openai"] = "configured"
        else:
            checks["azure_openai"] = "not_configured"
    except Exception as exc:
        checks["azure_openai"] = f"error: {exc}"

    # Session tracker summary
    try:
        tracker = get_global_tracker()
        checks["session_tracker"] = tracker.get_summary()
    except Exception as exc:
        checks["session_tracker"] = f"error: {exc}"

    all_ok = all(
        v == "ok" or v == "configured" or isinstance(v, dict) for v in checks.values()
    )
    return _json_response(
        {"status": "healthy" if all_ok else "degraded", "checks": checks},
        200 if all_ok else 503,
    )
