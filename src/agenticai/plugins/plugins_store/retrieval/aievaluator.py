import os
import logging
from typing import List, Dict, Annotated
from pydantic import BaseModel, ValidationError
from semantic_kernel.functions import kernel_function
from semantic_kernel.utils.logging import setup_logging
from utils.ml_logging import get_logger
from src.aoai.aoai_helper import AzureOpenAIManager

# Set up logging
setup_logging()
logging.getLogger("kernel").setLevel(logging.DEBUG)

TRACING_CLOUD_ENABLED = os.getenv("TRAINING_CLOUD_ENABLED") or False

class PolicyEvaluationResult(BaseModel):
    policies: List[str]
    reasoning: List[str]
    retry: bool

class AIPolicyEvaluationPlugin:
    """
    A plugin for evaluating search results against a search query to extract the most relevant policy paths.
    """

    def __init__(self) -> None:
        """
        Initialize the AIPolicyEvaluationPlugin with the necessary client configurations.
        """
        self.logger = get_logger(
            name="AIPolicyEvaluationPlugin", level=logging.DEBUG, tracing_enabled=TRACING_CLOUD_ENABLED
        )

        try:
            azure_openai_chat_deployment_id = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
            azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

            if not all([azure_openai_chat_deployment_id, azure_openai_key, azure_endpoint]):
                raise ValueError("One or more environment variables for OpenAI are missing.")

            self.azure_openai_client = AzureOpenAIManager(
                api_key=azure_openai_key,
                completion_model_name=azure_openai_chat_deployment_id,
                azure_endpoint=azure_endpoint,
            )

            self.EVALUATOR_PROMPT = """
            {EVALUATOR_INSTRUCTIONS}
            **Search Query**: "{query_text}"
            **Search Results**: {search_results}
            
            ## **Output Format**
            policies: ["path1", "path2"]
            reasoning: ["Reason 1", "Reason 2"]
            retry: false
            
            ## **Step-by-Step Reasoning**
            
            1. **Content Evaluation**:
                - **Step 1**: Read the **Search Query** to understand the user's request.
                - **Step 2**: For each search result, read the **Content** and compare it against the **Search Query**.
                - **Step 3**: Determine if the content is relevant and addresses the query's requirements.
                - **Step 4**: Mark the content as **“Approved”** if it is highly relevant and accurate.
            
            2. **Deduplication**:
                - **Step 1**: Compare the **Content** of each approved search result.
                - **Step 2**: Identify any content that is too similar or redundant.
                - **Step 3**: Select the most complete, clear, and useful version if multiple chunks are nearly identical.
            
            3. **Policy Extraction**:
                - **Step 1**: Extract the **Source Doc Path** from each approved content chunk.
                - **Step 2**: Ensure that no duplicate paths are included in the final list.
                - **Step 3**: Compile a list of unique, distinct, and relevant policy paths.
            
            4. **Reasoning**:
                - **Step 1**: For each search result, write a brief explanation of why it was accepted or rejected.
                - **Step 2**: If accepted, explain how the content addresses the query.
                - **Step 3**: If rejected, explain why the content was not relevant, incomplete, or inaccurate.
            
            ## **Example Output**
            
            policies: ["https://example.com/path/to/first/policy.pdf", "https://example.com/path/to/second/policy.pdf"]
            reasoning: [
                "Content from source https://example.com/path/to/first/policy.pdf was approved because it directly addressed the query regarding back pain treatment and policy details.",
                "Content from source https://example.com/path/to/second/policy.pdf was approved because it matched the clinical requirements for back pain treatment involving medication and physical therapy.",
                "Content from source https://example.com/path/to/third/policy.pdf was rejected because it only provided general information about health policies but did not mention back pain treatment specifically."
            ]
            retry: false
            """

            self.logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise e

    @kernel_function(
        name="evaluate_search_results", 
        description="Evaluates search results against a query to extract the most relevant policy paths."
    )
    async def evaluate_search_results(self, 
        query_text: Annotated[str, "The user's search query."], 
        search_results: Annotated[List[Dict[str, str]], "The list of search results to evaluate."]
    ) -> Annotated[PolicyEvaluationResult, "The evaluated result, containing policy paths, reasoning, and retry flag."]:
        """
        Evaluate search results against a query and extract the most relevant policy paths.
        
        :param query_text: The user's search query.
        :param search_results: A list of search results with details about source paths, content, and captions.
        :return: A PolicyEvaluationResult object containing policy paths, reasoning, and a retry flag.
        """
        try:
            self.logger.info(f"Evaluating search results for query: {query_text}")
            prompt = self.EVALUATOR_PROMPT.format(
                query_text=query_text,
                search_results=search_results,
                EVALUATOR_INSTRUCTIONS="""
                # Role: Retrieval Information Evaluator
                
                ## **Objective**
                Your role as the Evaluator is to analyze and evaluate the retrieved search results against the provided user query. Your goal is to **identify the most relevant policy or policies** that meet the user’s intent and **eliminate any duplicates or irrelevant content**.
                
                ## **Inputs**
                1. **Search Query**: The user's request for information.
                2. **Search Results**: A structured list of search results, each with the following attributes:
                   - 🆔 **ID**: The unique identifier for the content chunk.
                   - 📂 **Source Doc Path**: The URL or path to the source document.
                   - 📜 **Content**: The actual content or policy information extracted from the document.
                   - 💡 **Caption**: A short description or caption summarizing the key message in the content.
                
                
                ## **What You Need to Do**
                1. **Content Evaluation**:
                   - For each search result, determine if the **Content** from the source is relevant to the **Search Query**.
                   - Check if the content addresses the clinical or operational requirements stated in the query.
                   - If the content is highly relevant and accurately answers the query, mark it as **“Approved”**.
                
                2. **Deduplication**:
                   - Avoid selecting content that is too similar or redundant.
                   - If two or more chunks of content are nearly identical (even if from different sources), only select the most complete, clear, and useful version.
                
                3. **Policy Extraction**:
                   - Extract the **Source Doc Path** from the approved content.
                   - Ensure no duplicate paths are included.
                   - Multiple policies may be valid for a query, so you should return a list of unique, distinct, and relevant policy paths.
                
                4. **Reasoning**:
                   - For each search result, provide reasoning as to **why it was accepted or rejected**.
                   - If rejected, provide a clear explanation for why it was not relevant, incomplete, or inaccurate.
                """
            )
            response = await self.azure_openai_client.generate_chat_response(
                query=prompt,
                system_message_content=self.EVALUATOR_PROMPT,
                conversation_history=[],
                response_format="text",
                max_tokens=3000,
                temperature=0,  
            )
            raw_output = response["response"].strip()
            self.logger.debug(f"Raw AI output: {raw_output}")

            try:
                evaluation_result = PolicyEvaluationResult.model_validate_json(raw_output)
            except ValidationError as e:
                self.logger.error(f"Validation error: {e.json()}")
                return PolicyEvaluationResult(
                    policies=[],
                    reasoning=["Validation failed. Check if the AI output is a valid JSON structure."],
                    retry=True
                )

            self.logger.info("Search results evaluated successfully.")
            return evaluation_result

        except Exception as e:
            self.logger.error(f"Error during evaluation: {e}")
            return PolicyEvaluationResult(
                policies=[],
                reasoning=[f"Exception occurred: {str(e)}"],
                retry=True
            )
