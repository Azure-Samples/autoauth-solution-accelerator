"""
AI Search index manager for the Policy Indexer pipeline.

Handles index schema creation/update only — no skillsets, indexers, or
data sources. AI Search is used as a pure query engine.
"""

import logging
import os
import time
from typing import Any, Callable, Dict, Optional, TypeVar

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    VectorSearchProfile,
)

from .config import get_env, load_settings

logger = logging.getLogger("policy-indexer")

T = TypeVar("T")


def _retry_on_conflict(
    fn: Callable[..., T], *args, retries: int = 3, delay: float = 2.0, **kwargs
) -> T:
    """Retry a call if it hits a 409 Conflict (ETag / concurrent update)."""
    for attempt in range(retries):
        try:
            return fn(*args, **kwargs)
        except HttpResponseError as exc:
            if exc.status_code == 409 and attempt < retries - 1:
                logger.warning(
                    "Conflict on attempt %d/%d, retrying in %.1fs...",
                    attempt + 1,
                    retries,
                    delay,
                )
                time.sleep(delay)
            else:
                raise
    raise RuntimeError("Unreachable")


class IndexManager:
    """
    Manages the AI Search index schema.

    This is the only interaction with the AI Search management plane.
    No skillsets, indexers, or data source connections are created.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if config is None:
            config = load_settings()

        self.endpoint = get_env("AZURE_AI_SEARCH_SERVICE_ENDPOINT", required=True)
        search_admin_key = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
        if not search_admin_key:
            # Prefer managed-identity / Entra ID auth
            client_id = os.environ.get("AZURE_CLIENT_ID")
            self.credential = (
                DefaultAzureCredential(managed_identity_client_id=client_id)
                if client_id
                else DefaultAzureCredential()
            )
            logger.info("IndexManager using managed-identity auth for AI Search")
        else:
            # Fallback: admin key (local development)
            self.credential = AzureKeyCredential(search_admin_key)
            logger.info("IndexManager using admin key auth for AI Search")

        self.index_name = config["azure_search"]["index_name"]

        # OpenAI config (for vectorizer — still used at query time unless
        # the caller pre-vectorizes, in which case this is a no-op fallback)
        self.azure_openai_endpoint = get_env("AZURE_OPENAI_ENDPOINT", required=True)
        self.azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        self.azure_openai_embedding_deployment = get_env(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"
        )
        self.azure_openai_model_name = get_env(
            "AZURE_OPENAI_EMBEDDING_MODEL_NAME", "text-embedding-3-large"
        )
        self.azure_openai_model_dimensions = int(
            get_env("AZURE_OPENAI_EMBEDDING_DIMENSIONS", "3072")
        )

        self.add_page_numbers = config.get("index_settings", {}).get(
            "add_page_numbers", True
        )
        self.vector_search_config: Dict[str, Any] = config["vector_search"]

        self.index_client = SearchIndexClient(
            endpoint=self.endpoint, credential=self.credential
        )

    def create_or_update_index(self) -> str:
        """
        Create or update the AI Search index schema.

        Returns the index name.
        """
        fields = [
            SearchField(
                name="parent_id",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
            ),
            SearchField(
                name="title",
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name="parent_path",
                type=SearchFieldDataType.String,
            ),
            SearchField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                key=True,
                sortable=True,
                filterable=True,
                facetable=True,
                analyzer_name="keyword",
            ),
            SearchField(
                name="chunk",
                type=SearchFieldDataType.String,
                searchable=True,
                sortable=False,
                filterable=False,
                facetable=False,
            ),
            SearchField(
                name="vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=self.azure_openai_model_dimensions,
                vector_search_profile_name="myHnswProfile",
            ),
        ]

        if self.add_page_numbers:
            fields.append(
                SearchField(
                    name="page_number",
                    type=SearchFieldDataType.String,
                    sortable=True,
                    filterable=True,
                    facetable=False,
                )
            )

        # Vectorizer kwargs — prefer MI when no API key
        vectorizer_params_kwargs: Dict[str, Any] = {
            "resource_url": self.azure_openai_endpoint,
            "deployment_name": self.azure_openai_embedding_deployment,
            "model_name": self.azure_openai_model_name,
        }
        if self.azure_openai_key:
            vectorizer_params_kwargs["api_key"] = self.azure_openai_key

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name=self.vector_search_config["algorithms"][0]["name"],
                    parameters=HnswParameters(
                        m=self.vector_search_config["algorithms"][0]["parameters"]["m"],
                        ef_construction=self.vector_search_config["algorithms"][0][
                            "parameters"
                        ]["ef_construction"],
                        ef_search=self.vector_search_config["algorithms"][0][
                            "parameters"
                        ]["ef_search"],
                    ),
                ),
            ],
            profiles=[
                VectorSearchProfile(
                    name=self.vector_search_config["profiles"][0]["name"],
                    algorithm_configuration_name=self.vector_search_config["profiles"][
                        0
                    ]["algorithm_configuration_name"],
                    vectorizer_name=self.vector_search_config["profiles"][0][
                        "vectorizer_name"
                    ],
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name=self.vector_search_config["vectorizers"][0][
                        "vectorizer_name"
                    ],
                    parameters=AzureOpenAIVectorizerParameters(
                        **vectorizer_params_kwargs,
                    ),
                ),
            ],
        )

        semantic_config = SemanticConfiguration(
            name="my-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="chunk")]
            ),
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])

        index = SearchIndex(
            name=self.index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search,
        )

        result = _retry_on_conflict(self.index_client.create_or_update_index, index)
        logger.info("Index '%s' created/updated", result.name)
        return result.name

    def setup_all(self) -> Dict[str, str]:
        """
        Create/update the index. This is the only setup step needed now.

        Returns dict of created resource names.
        """
        index_name = self.create_or_update_index()
        return {"index": index_name}

    def get_index_stats(self) -> Dict[str, Any]:
        """Return basic index statistics."""
        try:
            stats = self.index_client.get_service_statistics()
            return {
                "index_name": self.index_name,
                "service_counters": (
                    str(stats.counters) if hasattr(stats, "counters") else "N/A"
                ),
            }
        except Exception as exc:
            return {"index_name": self.index_name, "error": str(exc)}
