import os
from typing import Any, Dict, List, Optional
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from utils.ml_logging import get_logger
from src.pipeline.utils import load_config
from src.storage.blob_helper import AzureBlobManager
from src.documentintelligence.document_intelligence_helper import AzureDocumentIntelligenceManager
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.promptEngineering.prompt_manager import PromptManager

class AgenticRAG:
    """
    Enhanced Retrieval-Augmented Generation (RAG) pipeline with sequential processing:
    1. Query Expansion
    2. Policy Retrieval
    3. Evaluation with retries if necessary.
    """

    def __init__(
        self,
        config_file: str = "agenticRag\\settings.yaml",
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        search_client: Optional[SearchClient] = None,
        azure_blob_manager: Optional[AzureBlobManager] = None,
        document_intelligence_client: Optional[AzureDocumentIntelligenceManager] = None,
        caseId: Optional[str] = None,
    ) -> None:
        
        self.config = load_config(config_file)
        self.run_config = self.config.get("run", {})
        self.query_expansion_config = self.config.get("query_expansion", {})
        self.policy_retrieval_config = self.config.get("retrieval", {})
        self.evaluation_config = self.config.get("evaluation", {})
        self.caseId = caseId
        self.prefix = f"[caseID: {self.caseId}] " if self.caseId else ""


        self.logger = get_logger(name=self.run_config['logging']['name'], 
                                 level=self.run_config['logging']['level'], 
                                 tracing_enabled=self.run_config['logging']['enable_tracing'])

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
            azure_search_admin_key = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
            search_client = SearchClient(endpoint=endpoint, 
                                         index_name=index_name, 
                                         credential=AzureKeyCredential(azure_search_admin_key))
        self.search_client = search_client

        self.blob_manager = azure_blob_manager or AzureBlobManager(
            storage_account_name=os.getenv("AZURE_STORAGE_ACCOUNT_NAME"),
            account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY"),
            container_name=self.run_config['azure_blob']['container_name']
        )

        self.document_intelligence_client = document_intelligence_client or AzureDocumentIntelligenceManager(
            azure_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
            azure_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        )
            
    async def expand_query(self, clinical_info: Any, 
                           system_message_content: Optional[str] = None,
                           max_tokens: Optional[int] = None,
                           top_p: Optional[float] = None,
                           temperature: Optional[float] = None,
                           frequency_penalty: Optional[float] = None,
                           presence_penalty: Optional[float] = None) -> str:
        """
        Expands the user-provided clinical information into an optimized query.
    
        Args:
            clinical_info (Any): Input clinical information.
            system_message_content (Optional[str]): System message content for the prompt. Defaults to self.SYSTEM_PROMPT_QUERY_EXPANSION.
            max_tokens (Optional[int]): Maximum number of tokens for the response. Defaults to self.max_tokens.
            top_p (Optional[float]): Top-p sampling parameter. Defaults to self.top_p.
            temperature (Optional[float]): Sampling temperature. Defaults to self.temperature.
            frequency_penalty (Optional[float]): Frequency penalty. Defaults to self.frequency_penalty.
            presence_penalty (Optional[float]): Presence penalty. Defaults to self.presence_penalty.
    
        Returns:
            str: Expanded query.
        """
        self.logger.info(f"{self.prefix}Expanding query...")
        
        # Use provided values or default to self attributes
        system_message_content = system_message_content or self.prompt_manager.get_prompt(self.query_expansion_config['system_prompt'])
        max_tokens = max_tokens or self.query_expansion_config['max_tokens'] 
        top_p = top_p or self.query_expansion_config['top_p']
        temperature = temperature or self.query_expansion_config['temperature']
        frequency_penalty = frequency_penalty or self.query_expansion_config['frequency_penalty']
        presence_penalty = presence_penalty or self.query_expansion_config['presence_penalty']

        prompt = self.prompt_manager.create_prompt_formulator_user(clinical_info)
        response = await self.azure_openai_client.generate_chat_response(
            query=prompt,
            system_message_content=system_message_content,
            conversation_history=[],
            response_format="json_object",
            max_tokens=max_tokens,
            top_p=top_p,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        return response.get("response", {}).get("optimized_query", "")
    
    def _format_azure_search_results(self, results: list, truncate: int = 2000) -> str:
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

    def retrieve_policies(
        self, 
        query: str, 
        k_nearest_neighbors: Optional[int] = None,
        weight: Optional[float] = None,
        top: Optional[int] = None,
        semantic_config: Optional[str] = None,
        vector_field: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves policies based on the expanded query.
        
        Args:
            query (str): Expanded query.
            k_nearest_neighbors (Optional[int]): Number of nearest neighbors to retrieve. Defaults to 5.
            weight (Optional[float]): Weight for the vector query. Defaults to 0.5.
            top (Optional[int]): Number of top results to retrieve. Defaults to 5.
            semantic_config (Optional[str]): Semantic configuration name. Defaults to "my-semantic-config".
            vector_field (Optional[str]): Fields to use for the vector query. Defaults to "vector".

        Returns:
            List[Dict[str, Any]]: Retrieved policy documents.
        """
        self.logger.info(f"{self.prefix}Retrieving policies...")
        semantic_config = self.policy_retrieval_config["semantic_configuration_name"] or semantic_config
        vector_field = self.policy_retrieval_config["vector_field"] or vector_field
        k_nearest_neighbors = self.policy_retrieval_config["k_nearest_neighbors"] or k_nearest_neighbors
        weight = self.policy_retrieval_config["weight"] or weight
        top = self.policy_retrieval_config["top"] or top

        vector_query = VectorizableTextQuery(
            text=query, k_nearest_neighbors=k_nearest_neighbors, fields=vector_field, weight=weight
        )
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=semantic_config,
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=top
        )
        return self._format_azure_search_results(results, truncate=2000)

    async def evaluate_results(self, query: str, search_results: List[Dict[str, Any]], 
                               system_message_content: Optional[str] = None,
                               max_tokens: Optional[int] = None,
                               top_p: Optional[float] = None,
                               temperature: Optional[float] = None,
                               frequency_penalty: Optional[float] = None,
                               presence_penalty: Optional[float] = None) -> Dict[str, Any]:
        """
        Evaluates the search results using Azure OpenAI.
    
        Args:
            query (str): Original user query.
            search_results (List[Dict[str, Any]]): Retrieved search results.
            system_message_content (Optional[str]): System message content for the prompt.
            conversation_history (Optional[List[Dict[str, Any]]]): Conversation history for the prompt. Defaults to an empty list.
            response_format (str): Format of the response. Defaults to "json_object".
            max_tokens (Optional[int]): Maximum number of tokens for the response. Defaults to self.max_tokens.
            top_p (Optional[float]): Top-p sampling parameter. Defaults to self.top_p.
            temperature (Optional[float]): Sampling temperature. Defaults to self.temperature.
            frequency_penalty (Optional[float]): Frequency penalty. Defaults to self.frequency_penalty.
            presence_penalty (Optional[float]): Presence penalty. Defaults to self.presence_penalty.
    
        Returns:
            Dict[str, Any]: Evaluation results with policies, reasoning, and retry flag.
        """
        self.logger.info(f"{self.prefix}Evaluating search results...")
        
        # Use provided values or default to self attributes
        system_message_content = system_message_content or self.prompt_manager.get_prompt(self.query_expansion_config['system_prompt'])
        max_tokens = max_tokens or self.query_expansion_config['max_tokens'] 
        top_p = top_p or self.query_expansion_config['top_p']
        temperature = temperature or self.query_expansion_config['temperature']
        frequency_penalty = frequency_penalty or self.query_expansion_config['frequency_penalty']
        presence_penalty = presence_penalty or self.query_expansion_config['presence_penalty']
    
        prompt = self.prompt_manager.create_prompt_evaluator_user(query, search_results)
        response = await self.azure_openai_client.generate_chat_response(
            query=prompt,
            system_message_content=system_message_content,
            conversation_history=[],
            response_format="json_object",
            max_tokens=max_tokens,
            top_p=top_p,
            temperature=temperature,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
        )
        self.logger.info(f'''{self.prefix}/n Evaluation response:
                         {response.get('response', {})}''')
        return response.get("response", {"policies": [], "reasoning": [], "retry": True})
    
    
    async def run(self, clinical_info: Any, max_retries: int = 3) -> Dict[str, Any]:
        """
        Orchestrates the complete RAG process:
        1. Query Expansion
        2. Policy Retrieval
        3. Evaluation
        with retries if necessary and minimal error handling.
    
        Args:
            clinical_info (Any): User-provided clinical information.
            max_retries (int): Maximum number of retries for the process. Default is 3.
    
        Returns:
            Dict[str, Any]: Dictionary containing the query, policies found, and evaluation results.
        """
    
        for attempt in range(max_retries):
            self.logger.info(f"{self.prefix}Starting AgenticRAG attempt {attempt + 1} of {max_retries}")
            try:
                # Step 1: Query Expansion
                expanded_query = await self.expand_query(clinical_info)
                if not expanded_query:
                    self.logger.warning(f"{self.prefix}Query expansion failed. Retrying...")
                    continue
    
                self.logger.info(f"{self.prefix}Expanded Query: {expanded_query}")
    
                # Step 2: Policy Retrieval
                search_results = self.retrieve_policies(expanded_query)
                if not search_results:
                    self.logger.warning(f"{self.prefix}No search results found. Retrying...")
                    continue
    
                self.logger.info(f"{self.prefix}Search results retrieved successfully")
    
                # Step 3: Evaluation
                evaluation = await self.evaluate_results(expanded_query, search_results)
                if not evaluation["retry"]:
                    self.logger.info(f"{self.prefix}Evaluation successful. Policies: {evaluation.get('policies', [])}")
                    return {
                        "query": expanded_query,
                        "policies": evaluation.get("policies", []),
                        "evaluation": evaluation
                    }
    
                self.logger.info(f"{self.prefix}Evaluation retry flag set to true. Retrying...")
            except Exception as e:
                self.logger.error(
                    f"{self.prefix}An unexpected error occurred on attempt {attempt + 1} of {max_retries}: {e}. Retrying..."
                )
                continue
    
        self.logger.error(f"{self.prefix}Max retries reached. Returning empty list of policies.")
        return {
            "query": None,
            "policies": [],
            "evaluation": None
        }