import os
from typing import Any, Dict, Optional
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from colorama import Fore
from utils.ml_logging import get_logger

from src.storage.blob_helper import AzureBlobManager
from src.documentintelligence.document_intelligence_helper import AzureDocumentIntelligenceManager
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.prompt_manager import PromptManager

class AgenticRAG:
    """
    This class handles Retrieval-Augmented Generation (RAG):
    - It expands the user's clinical information query.
    - Searches for relevant policy documents.
    - Retrieves and summarizes the policy as needed.

    If system prompts are not provided, they are fetched from the prompt_manager.
    """

    def __init__(
        self,
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        search_client: Optional[SearchClient] = None,
        azure_blob_manager: Optional[AzureBlobManager] = None,
        document_intelligence_client: Optional[AzureDocumentIntelligenceManager] = None,
        max_tokens: int = 2048,
        top_p: float = 0.8,
        temperature: float = 0.7,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        SYSTEM_PROMPT_QUERY_EXPANSION: Optional[str] = None,
        SYSTEM_PROMPT_SUMMARIZE_POLICY: Optional[str] = None,
        local: bool = False
    ) -> None:
        """
        Initialize the AgenticRAG.

        Args:
            azure_openai_client: AzureOpenAIManager instance. If None, initialized from env.
            prompt_manager: PromptManager instance for prompt templates. If None, new instance created.
            search_client: Azure SearchClient instance. If None, tries to init from environment.
            azure_blob_manager: AzureBlobManager. If None, tries to init from environment.
            document_intelligence_client: AzureDocumentIntelligenceManager. If None, init from env.
            max_tokens: Max tokens for LLM responses.
            top_p: top_p for LLM responses.
            temperature: Temperature for LLM responses.
            frequency_penalty: Frequency penalty for LLM responses.
            presence_penalty: Presence penalty for LLM responses.
            SYSTEM_PROMPT_QUERY_EXPANSION: System prompt for query expansion. If None, fetched from prompt_manager.
            SYSTEM_PROMPT_SUMMARIZE_POLICY: System prompt for policy summarization. If None, from prompt_manager.
            local: Whether to operate in local/tracing mode.
        """
        self.logger = get_logger(
            name="AgenticRAG", level=10, tracing_enabled=local
        )

        if azure_openai_client is None:
            api_key = os.getenv("AZURE_OPENAI_KEY", None)
            if api_key is None:
                self.logger.warning("No AZURE_OPENAI_KEY found. AgenticRAG may fail.")
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        self.prompt_manager = prompt_manager or PromptManager()

        if search_client is None:
            endpoint = os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT")
            index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
            search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=None)
        self.search_client = search_client

        if azure_blob_manager is None:
            account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
            azure_blob_manager = AzureBlobManager(
                storage_account_name=account_name,
                account_key=account_key,
                container_name="container"
            )
        self.blob_manager = azure_blob_manager

        if document_intelligence_client is None:
            endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
            key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
            document_intelligence_client = AzureDocumentIntelligenceManager(
                azure_endpoint=endpoint,
                azure_key=key
            )
        self.document_intelligence_client = document_intelligence_client

        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # Fallback to prompt_manager if not provided
        self.SYSTEM_PROMPT_QUERY_EXPANSION = SYSTEM_PROMPT_QUERY_EXPANSION or self.prompt_manager.get_prompt("query_expansion_system_prompt.jinja")
        self.SYSTEM_PROMPT_SUMMARIZE_POLICY = SYSTEM_PROMPT_SUMMARIZE_POLICY or self.prompt_manager.get_prompt("summarize_policy_system.jinja")

        self.local = local

    async def expand_query_and_search_policy(
        self, clinical_info: Any
    ) -> Dict[str, Any]:
        """
        Expand the user's clinical information into a more optimized query and search for relevant policy.

        Args:
            clinical_info: The clinical information (e.g. from extracted data).

        Returns:
            A dictionary containing an API response with an optimized query.
        """
        self.logger.info(Fore.CYAN + "Expanding query and searching for policy...")
        self.logger.info(f"Input clinical information: {clinical_info}")
        prompt_query_expansion = self.prompt_manager.create_prompt_query_expansion(clinical_info)
        api_response_query = await self.azure_openai_client.generate_chat_response(
            query=prompt_query_expansion,
            system_message_content=self.SYSTEM_PROMPT_QUERY_EXPANSION,
            conversation_history=[],
            response_format="json_object",
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        return api_response_query

    def locate_policy(self, api_response: Dict[str, Any]) -> str:
        """
        Locate the policy based on the optimized query from the AI response.

        Args:
            api_response: The AI response containing the optimized query.

        Returns:
            The path/URL of the located policy or an error message if not found.
        """
        try:
            optimized_query = api_response["response"]["optimized_query"]
            vector_query = VectorizableTextQuery(
                text=optimized_query, k_nearest_neighbors=5, fields="vector", weight=0.5
            )

            results = self.search_client.search(
                search_text=optimized_query,
                vector_queries=[vector_query],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                top=5,
            )

            first_result = next(iter(results), None)
            if first_result:
                parent_path = first_result.get("parent_path", "Path not found")
                return parent_path
            else:
                self.logger.warning("No results found")
                return "No results found"
        except Exception as e:
            self.logger.error(f"Error locating policy: {e}")
            return "Error locating policy"

    def get_policy_text_from_blob(self, blob_url: str) -> str:
        """
        Retrieve policy text from the specified blob URL using Document Intelligence.

        Args:
            blob_url: The URL to the policy blob.

        Returns:
            The text content of the downloaded policy document.
        """
        try:
            blob_content = self.blob_manager.download_blob_to_bytes(blob_url)
            if blob_content is None:
                raise Exception(f"Failed to download blob from URL: {blob_url}")
            self.logger.info(f"Blob content downloaded successfully from {blob_url}")

            policy_text = self.document_intelligence_client.analyze_document(
                document_input=blob_content,
                model_type="prebuilt-layout",
                output_format="markdown",
            )
            self.logger.info(f"Document analyzed successfully for blob {blob_url}")
            return policy_text.content
        except Exception as e:
            self.logger.error(f"Failed to get policy text from blob {blob_url}: {e}")
            return ""

    async def summarize_policy(self, policy_text: str) -> str:
        """
        Summarize a given policy text using the LLM.

        Args:
            policy_text: The full text of the policy document.

        Returns:
            A summarized version of the policy text.
        """
        self.logger.info(Fore.CYAN + "Summarizing Policy...")
        prompt_user_query_summary = self.prompt_manager.create_prompt_summary_policy(policy_text)
        api_response_query = await self.azure_openai_client.generate_chat_response(
            query=prompt_user_query_summary,
            system_message_content=self.SYSTEM_PROMPT_SUMMARIZE_POLICY,
            conversation_history=[],
            response_format="text",
            max_tokens=4096,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        return api_response_query["response"]
