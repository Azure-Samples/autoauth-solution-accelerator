"""
Text chunker for the Policy Indexer pipeline.

Replicates Azure AI Search SplitSkill behavior (character-based page splitting
with configurable overlap) without any dependency on AI Search skillsets.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger("policy-indexer")


@dataclass
class Chunk:
    """A single text chunk with its metadata."""

    text: str
    index: int
    page_number: Optional[str] = None
    start_char: int = 0
    end_char: int = 0


@dataclass
class ChunkerConfig:
    """Configuration for the text chunker — mirrors SplitSkill parameters."""

    max_chunk_length: int = 3000
    overlap_length: int = 500
    split_mode: str = "pages"  # character-based splitting


class TextChunker:
    """
    Splits text into overlapping chunks, matching the behaviour of the
    Azure AI Search SplitSkill with ``text_split_mode=pages``.
    """

    def __init__(self, config: Optional[ChunkerConfig] = None):
        self.config = config or ChunkerConfig()

    def chunk_text(
        self,
        text: str,
        page_number: Optional[str] = None,
    ) -> List[Chunk]:
        """
        Split *text* into chunks of at most ``max_chunk_length`` characters
        with ``overlap_length`` overlap between consecutive chunks.

        Args:
            text: The text to split.
            page_number: Optional page number to attach to each chunk.

        Returns:
            List of Chunk objects.
        """
        max_len = self.config.max_chunk_length
        overlap = self.config.overlap_length
        chunks: List[Chunk] = []

        if not text or not text.strip():
            return chunks

        start = 0
        idx = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + max_len, text_len)

            # Try to break at a sentence/word boundary if we're not at the end
            if end < text_len:
                # Look backwards from end to find a good break point
                break_at = self._find_break_point(text, start, end)
                if break_at > start:
                    end = break_at

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=idx,
                        page_number=page_number,
                        start_char=start,
                        end_char=end,
                    )
                )
                idx += 1

            # Advance: next chunk starts (end - overlap) characters into the current chunk
            next_start = end - overlap
            if next_start <= start:
                # Ensure forward progress
                next_start = end
            start = next_start

        return chunks

    def chunk_pages(
        self,
        pages: List[dict],
    ) -> List[Chunk]:
        """
        Chunk a list of page dicts (from OCR extraction).

        Each page dict should have ``text`` and optionally ``page_number``.
        Chunks from all pages are concatenated with a global index.

        Args:
            pages: List of dicts with keys ``text`` and ``page_number``.

        Returns:
            List of Chunk objects with globally sequential indices.
        """
        all_chunks: List[Chunk] = []
        global_idx = 0

        for page in pages:
            page_text = page.get("text", "")
            page_num = str(page.get("page_number", ""))

            page_chunks = self.chunk_text(page_text, page_number=page_num)
            for chunk in page_chunks:
                chunk.index = global_idx
                global_idx += 1
                all_chunks.append(chunk)

        return all_chunks

    @staticmethod
    def _find_break_point(text: str, start: int, end: int) -> int:
        """
        Look backwards from *end* to find a sentence or word boundary.
        Returns the position to break at, or *end* if no good break found
        within a reasonable window.
        """
        # Search window: last 20% of the chunk
        window_start = max(start, end - (end - start) // 5)

        # Prefer sentence boundaries
        for sep in ("\n\n", "\n", ". ", "? ", "! ", "; "):
            pos = text.rfind(sep, window_start, end)
            if pos > window_start:
                return pos + len(sep)

        # Fall back to word boundary
        pos = text.rfind(" ", window_start, end)
        if pos > window_start:
            return pos + 1

        return end

    @staticmethod
    def generate_chunk_id(blob_name: str, chunk_index: int) -> str:
        """
        Generate a deterministic, unique chunk ID.

        Format: ``<sha256(blob_name)[:16]>_chunk_<index>``
        """
        blob_hash = hashlib.sha256(blob_name.encode("utf-8")).hexdigest()[:16]
        return f"{blob_hash}_chunk_{chunk_index}"

    @staticmethod
    def generate_parent_id(blob_name: str) -> str:
        """Generate a deterministic parent ID from the blob name."""
        return hashlib.sha256(blob_name.encode("utf-8")).hexdigest()[:16]
