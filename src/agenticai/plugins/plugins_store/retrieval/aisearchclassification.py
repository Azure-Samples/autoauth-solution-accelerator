import logging
import os
from typing import Annotated

from semantic_kernel.functions import kernel_function
from semantic_kernel.utils.logging import setup_logging

from src.aoai.aoai_helper import AzureOpenAIManager
from utils.ml_logging import get_logger

# Set up logging
setup_logging()
logging.getLogger("kernel").setLevel(logging.DEBUG)

TRACING_CLOUD_ENABLED = os.getenv("TRAINING_CLOUD_ENABLED") or False


class AIQueryClassificationPlugin:
    """
    A plugin for intelligent query classification and search, leveraging LLMs for classification.
    This plugin can classify a query as 'keyword', 'semantic', or 'hybrid'
    """

    def __init__(self) -> None:
        """
        Initialize the AIQueryClassificationPlugin with the necessary client configurations.
        """
        self.logger = get_logger(
            name="AIQueryClassificationPlugin",
            level=logging.DEBUG,
            tracing_enabled=TRACING_CLOUD_ENABLED,
        )

        try:
            azure_openai_chat_deployment_id = os.getenv(
                "AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
            )
            azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")

            if not all(
                [azure_openai_chat_deployment_id, azure_openai_key, azure_endpoint]
            ):
                raise ValueError(
                    "One or more environment variables for OpenAI are missing."
                )

            self.azure_openai_client = AzureOpenAIManager(
                api_key=azure_openai_key,
                completion_model_name=azure_openai_chat_deployment_id,
                azure_endpoint=azure_endpoint,
            )

            self.SYSTEM_PROMPT_QUERY_CLASSIFICATION = """
            You are an intelligent Query Classification Assistant. Your role is to analyze and classify the following search query into one of two categories: 'keyword' or 'semantic'.

            ## Objective:
            Your task is to choose the most effective search strategy for the query to achieve maximum relevance and retrieval performance. Use the following guidelines to classify the query.

            ## Core Definitions:
            - **Keyword Search**: Used when the query contains specific terms, exact matches, or entity-based lookups (like names, numbers, or product codes). These queries are short, direct, and usually contain very specific phrasing.
            - **Semantic Search**: Used when the query is a natural language question, conversational, requires contextual understanding, or involves multiple concepts that may require disambiguation. This includes ambiguous, complex, or multi-intent queries that cannot be satisfied by exact matches alone.

            ---

            ## Step-by-step Chain-of-Thought Process:
            1. **Check for Specific Terms or Entity Matches**:
               - Does the query contain proper nouns, names, product IDs, or highly specific terms?
               - Is the query concise (typically fewer than 5 words) and focused on a specific known entity?
               - If YES to both, classify as **'keyword'**.

            2. **Otherwise**:
               - Classify as **'semantic'**, which includes queries that are natural language questions, verbose, exploratory, ambiguous, or involve multiple related terms or concepts that require contextual understanding.

            ---

            ## Examples of Queries and Their Classifications:
            - **"Policy for Adalimumab for Crohn's Disease"** → **'keyword'** (Entity-based search with clear specificity)
            - **"What is the process for prior authorization for Humira?"** → **'semantic'** (Natural language query requiring contextual understanding)
            - **"Prior authorization for Adalimumab and Anemia treatment options"** → **'semantic'** (Multiple concepts and potential ambiguity)
            - **"Crohn's Disease"** → **'keyword'** (Specific and focused)
            - **"Best therapy for Crohn's Disease based on 2023 guidelines"** → **'semantic'** (Exploratory natural language search)
            - **"Adalimumab for Crohn's Disease and IBD with biologic therapy options"** → **'semantic'** (Multiple overlapping concepts and contextual needs)

            ---

            ## Final Instructions:
            1. **Apply the Chain-of-Thought Reasoning** outlined above to classify the query.
            2. Respond with one and only one of the following: **'keyword'** or **'semantic'**.
            3. Your response must be clear and contain only one word.

            ---

            **Query: "{query_text}"**

            ---

            **Response (only one of these two options):**
            - 'keyword'
            - 'semantic'
            """

            self.logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise e

    @kernel_function(
        name="classify_search_query",
        description="Classifies a query into 'keyword', 'semantic', or 'hybrid' using LLM reasoning.",
    )
    async def classify_query(
        self, query_text: Annotated[str, "The user's search query to be classified."]
    ) -> Annotated[
        str, "The classification for the query as 'keyword', 'semantic', or 'hybrid'."
    ]:
        """
        Classify the query as 'keyword', 'semantic', or 'hybrid' using an LLM.

        :param query_text: The user's search query.
        :return: A classification as 'keyword', 'semantic', or 'hybrid'.
        """
        try:
            self.logger.info(f"Classifying query: {query_text}")

            prompt = self.SYSTEM_PROMPT_QUERY_CLASSIFICATION.format(
                query_text=query_text
            )

            response = await self.azure_openai_client.generate_chat_response(
                query=prompt,
                system_message_content=self.SYSTEM_PROMPT_QUERY_CLASSIFICATION,
                conversation_history=[],
                response_format="text",
                max_tokens=10,
                temperature=0,  # Ensuring deterministic responses
            )
            classification = response["response"].strip().lower()

            if classification not in {"keyword", "semantic", "hybrid"}:
                self.logger.warning(
                    f"Invalid classification: '{classification}', defaulting to 'semantic'."
                )
                classification = "semantic"

            self.logger.info(f"Query classified as: {classification}")
            return classification

        except Exception as e:
            self.logger.error(f"Error during query classification: {e}")
            return "semantic"
