import os
import logging
from typing import Annotated, Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from azure.core.credentials import AzureKeyCredential
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.functions import kernel_function
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from utils.ml_logging import get_logger
from semantic_kernel.utils.logging import setup_logging

# Set up logging
setup_logging()
logging.getLogger("kernel").setLevel(logging.DEBUG)

TRACING_CLOUD_ENABLED = os.getenv("TRAINING_CLOUD_ENABLED") or False

class AzureSearchPlugin:
    """
    A plugin for interacting with Azure AI Search, supporting three distinct search methods:
    1. Keyword Search
    2. Semantic Search
    3. Hybrid Search
    """

    def __init__(self) -> None:
        """
        Initialize the AzureSearchPlugin with the necessary client configurations.
        """
        self.logger = get_logger(
            name="AgenticRAG - Plugin AzureSearchPlugin", level=10, tracing_enabled=TRACING_CLOUD_ENABLED
        )
        
        try:
            endpoint = os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT")
            index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
            api_key = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
            if not all([endpoint, index_name, api_key]):
                raise ValueError("One or more environment variables for Azure Search are missing.")
            self.logger.info(f"Initializing SearchClient with endpoint: {endpoint}, index_name: {index_name}")
            credential = AzureKeyCredential(api_key)
            self.search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=credential)
            self.logger.info("SearchClient initialized successfully.")
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise e

    @kernel_function(
        name="keyword_search",
        description="Performs a keyword-based search against the Azure AI Search index."
    )
    def keyword_search(
        self, 
        search_text: str, 
        top: int = 5
    ) -> Annotated[List[Dict[str, Any]], "A list of search results for the keyword query"]:
        """
        Executes a keyword-based search on the index.
        
        :param search_text: The text to search for using keyword search.
        :param top: The maximum number of results to return.
        :return: A list of search results.
        """
        function_id = "keyword_search"
        self.logger.info(f"Function {function_id} called.")
        try:
            results = self.search_client.search(
                search_text=search_text,
                query_type=QueryType.SIMPLE,
                top=top
            )
            extracted_results = self._format_azure_search_results(results)
            logging.info(f"Extracted results: {extracted_results}")
            self.logger.info(f"Extracted results: {extracted_results}")
            return extracted_results
        except Exception as e:
            self.logger.error(f"{function_id} - Error during keyword search: {e}")
            return []
        
    def _format_azure_search_results(self, results: list, truncate: int = 1000) -> str:
        """
        Formats Azure AI Search results into a structured, readable string.
        
        Each result contains:
        - Chunk ID
        - Reranker Score
        - Source Document Path
        - Content (truncated to the specified number of characters if too long)
        - Caption (highlighted if available)
        
        :param results: List of results from the Azure AI Search API.
        :param truncate: Maximum number of characters to include in the content before truncating.
        :return: Formatted string representation of the search results.
        """
        formatted_results = []

        for result in results:
            # Access all properties like a dictionary
            chunk_id = result['chunk_id'] if 'chunk_id' in result else 'N/A'
            reranker_score = result['@search.reranker_score'] if '@search.reranker_score' in result else 'N/A'
            source_doc_path = result['parent_path'] if 'parent_path' in result else 'N/A'
            content = result['chunk'] if 'chunk' in result else 'N/A'
            
            # Truncate content to specified number of characters
            content = content[:truncate] + "..." if len(content) > truncate else content

            # Extract caption (highlighted caption if available)
            captions = result['@search.captions'] if '@search.captions' in result else []
            caption = "Caption not available"
            if captions:
                first_caption = captions[0]
                if first_caption.highlights:
                    caption = first_caption.highlights
                elif first_caption.text:
                    caption = first_caption.text

            # Format each result section
            result_string = (
                f"========================================\n"
                f"🆔 ID: {chunk_id}\n"
                f"📂 Source Doc Path: {source_doc_path}\n"
                f"📜 Content: {content}\n"
                f"💡 Caption: {caption}\n"
                f"========================================"
            )

            formatted_results.append(result_string)

        # Join all the formatted results into a single string
        return "\n\n".join(formatted_results)


    @kernel_function(
        name="semantic_search",
        description="Performs a semantic search using Azure AI Search."
    )
    def semantic_search(
        self, 
        search_text: str, 
        top: int = 5
    ) -> Annotated[List[Dict[str, Any]], "A list of search results for the semantic query"]:
        """
        Executes a semantic search on the index.
        
        :param search_text: The text to search for using semantic search.
        :param top: The maximum number of results to return.
        :return: A list of search results.
        """
        function_id = "semantic_search"
        self.logger.info(f"Function {function_id} called.")
        try:
            vector_query = VectorizableTextQuery(
                text=search_text, k_nearest_neighbors=5, fields="vector", weight=0.5
            )
            results = self.search_client.search(
                search_text=search_text,
                vector_queries=[vector_query],
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="my-semantic-config",
                query_caption=QueryCaptionType.EXTRACTIVE,
                query_answer=QueryAnswerType.EXTRACTIVE,
                top=top
            )
            extracted_results = self._format_azure_search_results(results)
            logging.info(f"Extracted results: {extracted_results}")
            self.logger.info(f"Extracted results: {extracted_results}")
            return extracted_results
        except Exception as e:
            self.logger.error(f"{function_id} - Error during semantic search: {e}")
            return []

    @kernel_function(
        name="hybrid_search",
        description="Performs a hybrid search using both keyword and vector search techniques."
    )
    def hybrid_search(
        self, 
        search_text: str, 
        top: int = 5
    ) -> Annotated[List[Dict[str, Any]], "A list of search results for the hybrid query"]:
        """
        Executes a hybrid search on the index, combining keyword and vector-based search.
        
        :param search_text: The text to search for using the hybrid search approach.
        :param top: The maximum number of results to return.
        :return: A list of search results.
        """
        function_id = "hybrid_search"
        self.logger.info(f"Function {function_id} called.")
        vector_query = VectorizableTextQuery(
                text=search_text, k_nearest_neighbors=5, fields="vector", weight=0.5
            )
        try:
            results = self.search_client.search(
                vector_queries=[vector_query],
                search_text=search_text,
                query_type=QueryType.SIMPLE,
                top=top
            )
            extracted_results = self._extract_search_results(results)
            print(extracted_results)
            return extracted_results
        except Exception as e:
            self.logger.error(f"{function_id} - Error during hybrid search: {e}")
            return []