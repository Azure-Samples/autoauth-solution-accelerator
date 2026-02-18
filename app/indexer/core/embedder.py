"""
Azure OpenAI embedding client for the Policy Indexer pipeline.

Handles batched embedding generation with exponential backoff retry,
configurable batch sizes, and rate-limit awareness.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import List, Optional

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

logger = logging.getLogger("policy-indexer")


@dataclass
class EmbedderConfig:
    """Configuration for the embedding client."""

    deployment: str = ""
    model_name: str = "text-embedding-3-large"
    dimensions: int = 3072
    batch_size: int = 16  # Azure OpenAI supports up to 16 texts per request
    max_retries: int = 5
    base_retry_delay: float = 2.0  # seconds


class Embedder:
    """
    Generates embeddings via Azure OpenAI with batching and retry.

    Supports both API-key and managed-identity authentication.
    """

    def __init__(self, config: Optional[EmbedderConfig] = None):
        self.config = config or EmbedderConfig()

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        api_key = os.environ.get("AZURE_OPENAI_KEY")

        self.config.deployment = self.config.deployment or os.environ.get(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"
        )
        self.config.model_name = self.config.model_name or os.environ.get(
            "AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large"
        )
        self.config.dimensions = self.config.dimensions or int(
            os.environ.get("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "3072")
        )

        api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01")

        if not api_key:
            # Prefer managed-identity / Entra ID auth
            client_id = os.environ.get("AZURE_CLIENT_ID")
            credential = (
                DefaultAzureCredential(managed_identity_client_id=client_id)
                if client_id
                else DefaultAzureCredential()
            )
            token_provider = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
            self.client = AzureOpenAI(
                azure_ad_token_provider=token_provider,
                api_version=api_version,
                azure_endpoint=endpoint,
            )
            logger.info("Embedder using managed-identity auth")
        else:
            # Fallback: API key (local development)
            self.client = AzureOpenAI(
                api_key=api_key,
                api_version=api_version,
                azure_endpoint=endpoint,
            )
            logger.info("Embedder using API key auth")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts, automatically batching
        and retrying on rate-limit errors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors (each a list of floats), in the same
            order as the input texts.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = [[] for _ in range(len(texts))]
        batch_size = self.config.batch_size

        for batch_start in range(0, len(texts), batch_size):
            batch_end = min(batch_start + batch_size, len(texts))
            batch = texts[batch_start:batch_end]

            batch_embeddings = self._embed_batch_with_retry(batch)

            for i, emb in enumerate(batch_embeddings):
                all_embeddings[batch_start + i] = emb

            if batch_end < len(texts):
                logger.info("Embedded %d/%d texts", batch_end, len(texts))

        return all_embeddings

    def embed_single(self, text: str) -> List[float]:
        """Embed a single text string. Convenience wrapper."""
        results = self.embed_texts([text])
        return results[0] if results else []

    def _embed_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        """Embed a single batch with exponential backoff on rate-limit errors."""
        delay = self.config.base_retry_delay

        for attempt in range(1, self.config.max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    input=texts,
                    model=self.config.deployment,
                    dimensions=self.config.dimensions,
                )
                # Sort by index to ensure order matches input
                sorted_data = sorted(response.data, key=lambda d: d.index)
                return [d.embedding for d in sorted_data]

            except Exception as exc:
                error_str = str(exc).lower()
                is_rate_limit = (
                    "rate" in error_str
                    or "429" in error_str
                    or "throttl" in error_str
                    or "retry" in error_str
                )

                if is_rate_limit and attempt < self.config.max_retries:
                    logger.warning(
                        "Rate limited on embedding attempt %d/%d, retrying in %.1fs: %s",
                        attempt,
                        self.config.max_retries,
                        delay,
                        exc,
                    )
                    time.sleep(delay)
                    delay = min(delay * 2, 60.0)  # cap at 60s
                else:
                    logger.error(
                        "Embedding failed on attempt %d/%d: %s",
                        attempt,
                        self.config.max_retries,
                        exc,
                    )
                    raise

        raise RuntimeError("Unreachable")  # satisfy type checker
