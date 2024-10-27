import os
import asyncio
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from colorama import Fore, init
from src.aoai.azure_openai import AzureOpenAIManager
from app.components.prompts import (
    SYSTEM_PROMPT_NER,
    SYSTEM_PROMPT_PRIOR_AUTH,
    SYSTEM_PROMPT_QUERY_EXPANSION,
    create_prompt_pa,
    create_prompt_query_expansion,
    USER_PROMPT_NER,
)
from src.extractors.pdf_data_extractor import OCRHelper
from src.documentintelligence.document_intelligence_helper import AzureDocumentIntelligenceManager
from src.entraid.generate_id import generate_unique_id
from src.cosmosdb.cosmosdb_helper import CosmosDBManager
from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger

# Initialize colorama and logger
init(autoreset=True)
logger = get_logger()

# Load environment variables
dotenv.load_dotenv(".env")

class PAProcessingPipeline:
    """
    A class to handle the Prior Authorization Processing Pipeline.

    Attributes:
        azure_openai_client (AzureOpenAIManager): The Azure OpenAI client.
        search_client (SearchClient): The Azure Search client.
        container_name (str): The name of the Azure Blob Storage container.
        temp_dir (str): The path to the temporary directory for storing processed files.
        case_id (str): A unique ID for the case.
        conversation_history (Dict[str, Any]): A dictionary to store the conversation history.
        local (bool): Flag indicating whether operations are local or involve Azure services.
        cosmos_db_manager (Optional[CosmosDBManager]): The CosmosDB manager for remote mode.
        blob_manager (Optional[AzureBlobManager]): The Blob storage manager for remote mode.
        document_intelligence_client (AzureDocumentIntelligenceManager): The Document Intelligence client.
    """

    def __init__(
        self,
        azure_openai_chat_deployment_id: Optional[str] = None,
        azure_openai_key: Optional[str] = None,
        azure_search_service_endpoint: Optional[str] = None,
        azure_search_index_name: Optional[str] = None,
        azure_search_admin_key: Optional[str] = None,
        azure_blob_container_name: str = "pre-auth-policies",
        temp_dir_base_path: str = "utils/temp",
        azure_blob_storage_account_name: Optional[str] = None,
        azure_blob_storage_account_key: Optional[str] = None,
        local: bool = True,
        azure_cosmos_db_endpoint: Optional[str] = None,
        azure_cosmos_db_key: Optional[str] = None,
        azure_cosmos_db_database_name: Optional[str] = None,
        azure_cosmos_db_container_name: Optional[str] = None,
        azure_document_intelligence_endpoint: Optional[str] = None,
        azure_document_intelligence_key: Optional[str] = None,
        caseId: Optional[str] = None,
    ):
        """
        Initialize the PAProcessingPipeline with provided parameters or environment variables.

        Args:
            azure_openai_chat_deployment_id (Optional[str]): The Azure OpenAI Chat Deployment ID.
            azure_openai_key (Optional[str]): The Azure OpenAI key.
            azure_search_service_endpoint (Optional[str]): The Azure Search Service Endpoint.
            azure_search_index_name (Optional[str]): The Azure Search Index Name.
            azure_search_admin_key (Optional[str]): The Azure Search Admin Key.
            azure_blob_container_name (str): The Azure Blob Storage Container Name.
            temp_dir_base_path (str): The base path for the temporary directory.
            azure_blob_storage_account_name(Optional[str]): The Azure Blob Storage Account Name.
            azure_blob_storage_account_key(Optional[str]): The Azure Blob Storage Account Key.
            local (bool): Flag indicating whether operations are local or involve Azure services.
            azure_cosmos_db_endpoint (Optional[str]): The endpoint URL for Azure Cosmos DB.
            azure_cosmos_db_key (Optional[str]): The access key for Azure Cosmos DB.
            azure_cosmos_db_database_name (Optional[str]): The name of the Cosmos DB database.
            azure_cosmos_db_container_name (Optional[str]): The name of the Cosmos DB container.
            azure_document_intelligence_endpoint (Optional[str]): The endpoint URL for Azure Document Intelligence.
            azure_document_intelligence_key (Optional[str]): The access key for Azure Document Intelligence.
            case_id (Optional[str]): A unique ID for the case.
        """
        # Load environment variables if not provided
        if not azure_openai_chat_deployment_id:
            azure_openai_chat_deployment_id = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
        if not azure_openai_key:
            azure_openai_key = os.getenv("AZURE_OPENAI_KEY")
        if not azure_search_service_endpoint:
            azure_search_service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
        if not azure_search_index_name:
            azure_search_index_name = os.getenv("AZURE_SEARCH_INDEX_NAME")
        if not azure_search_admin_key:
            azure_search_admin_key = os.getenv("AZURE_SEARCH_ADMIN_KEY")
        if not azure_blob_storage_account_name:
            azure_blob_storage_account_name= os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        if not azure_blob_storage_account_key:
            azure_blob_storage_account_key= os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        if not azure_cosmos_db_endpoint:
            azure_cosmos_db_endpoint = os.getenv("AZURE_COSMOS_DB_ENDPOINT")
        if not azure_cosmos_db_key:
            azure_cosmos_db_key = os.getenv("AZURE_COSMOS_DB_KEY")
        if not azure_cosmos_db_database_name:
            azure_cosmos_db_database_name = os.getenv("AZURE_COSMOS_DB_DATABASE_NAME")
        if not azure_cosmos_db_container_name:
            azure_cosmos_db_container_name = os.getenv("AZURE_COSMOS_DB_CONTAINER_NAME")
        if not azure_document_intelligence_endpoint:
            azure_document_intelligence_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        if not azure_document_intelligence_key:
            azure_document_intelligence_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Initialize attributes
        self.azure_openai_client = AzureOpenAIManager(
            completion_model_name=azure_openai_chat_deployment_id,
            api_key=azure_openai_key,
        )
        self.search_client = SearchClient(
            endpoint=azure_search_service_endpoint,
            index_name=azure_search_index_name,
            credential=AzureKeyCredential(azure_search_admin_key),
        )
        self.container_name = azure_blob_container_name
        self.case_id = caseId if caseId else generate_unique_id()
        self.conversation_history: Dict[str, Any] = {}
        self.local = local
        self.azure_blob_storage_account_name = azure_blob_storage_account_name
        self.azure_blob_storage_account_key = azure_blob_storage_account_key
        self.document_intelligence_client = AzureDocumentIntelligenceManager(
            azure_endpoint=azure_document_intelligence_endpoint, 
            azure_key=azure_document_intelligence_key
        )
        # Initialize CosmosDBManager and AzureBlobManager if local is False
        self.blob_manager = AzureBlobManager(
            storage_account_name=self.azure_blob_storage_account_name,
            account_key=self.azure_blob_storage_account_key,
            container_name=self.container_name,
        )
        if not self.local:
            self.cosmos_db_manager = CosmosDBManager(
                endpoint_url=azure_cosmos_db_endpoint,
                credential_id=azure_cosmos_db_key,
                database_name=azure_cosmos_db_database_name,
                container_name=azure_cosmos_db_container_name,
            )
            self.temp_dir = f"{self.container_name}/{self.case_id}"
        else:
            self.cosmos_db_manager = None
            self.blob_manager = None
            self.temp_dir = os.path.join(temp_dir_base_path, self.case_id)
            os.makedirs(self.temp_dir, exist_ok=True)

    def analyze_document(self, document_path: str) -> Dict[str, Any]:
        """
        Analyze a document using Azure Document Intelligence.

        Args:
            document_path (str): The path to the document to be analyzed.

        Returns:
            Dict[str, Any]: The analysis results.
        """
        with open(document_path, "rb") as document:
            analysis_result = self.document_intelligence_client.analyze_document(document)
        return analysis_result

    def locate_policy(self, api_response: Dict[str, Any]) -> str:
        """
        Locate the policy based on the optimized query from the AI response.

        Args:
            api_response (Dict[str, Any]): The AI response containing the optimized query.

        Returns:
            str: The location of the policy or a message indicating no results were found.
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
                return "No results found"
        except Exception as e:
            logger.error(f"Error locating policy: {e}")
            return "Error locating policy"

    def process_uploaded_files(self, uploaded_files: List[str]) -> str:
        """
        Process uploaded files and extract images.

        Args:
            uploaded_files (List[str]): List of file paths to the uploaded files.

        Returns:
            str: Path to the directory containing processed images.
        """
        ocr_helper = OCRHelper(container_name=self.container_name)
        temp_dir = self.temp_dir

        try:
            for file_path in uploaded_files:
                logger.info(f"Processing file: {file_path}")
                # For both local and remote, extract images locally
                ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=temp_dir
                )

            logger.info(f"Files processed and images extracted to: {temp_dir}")

            if not self.local and self.blob_manager:
                # Upload the extracted images to Azure Blob Storage
                self.blob_manager.upload_files(
                    local_path=temp_dir,
                    remote_path=temp_dir,
                    overwrite=True,
                )
                logger.info(f"Images uploaded to Azure Blob Storage at {temp_dir}")

            return temp_dir
        except Exception as e:
            logger.error(f"Failed to process files: {e}")
            return temp_dir

    def get_policy_text_from_blob(self, blob_url: str) -> str:
        """
        Download the blob content from the given URL and extract text.

        Args:
            blob_url (str): The URL of the blob.

        Returns:
            str: The extracted text from the document.
        """
        document_intelligence_client = AzureDocumentIntelligenceManager()
        try:
            parsed_url = urllib.parse.urlparse(blob_url)
            blob_name = parsed_url.path.lstrip('/')
            container_name = parsed_url.netloc.split('.')[0]

            if self.local:           
                blob_content = self.blob_manager.download_blob_to_bytes(blob_name)
                if blob_content is None:
                    raise Exception(f"Failed to download blob {blob_name}")
                logger.info(f"Blob content downloaded successfully from {blob_url}")
            else:
                self.blob_manager.change_container(container_name)
                blob_content = self.blob_manager.download_blob_to_bytes(blob_name)
                if blob_content is None:
                    raise Exception(f"Failed to download blob {blob_name}")
                logger.info(f"Blob content downloaded successfully from {blob_url}")

            # Analyze the document
            policy_text = document_intelligence_client.analyze_document(
                document_input=blob_content,
                model_type="prebuilt-layout",
                output_format="markdown",
            )
            logger.info(f"Document analyzed successfully for blob {blob_url}")
            return policy_text.content
        except Exception as e:
            logger.error(f"Failed to get policy text from blob {blob_url}: {e}")
            return ""


    def find_all_files(
        self, root_folder: str, extensions: Union[List[str], str]
    ) -> List[str]:
        """
        Recursively find all files with specified extensions under the root folder.

        Args:
            root_folder (str): The root folder to search for files.
            extensions (Union[List[str], str]): List of file extensions to search for.

        Returns:
            List[str]: List of full paths to the found files.
        """
        if isinstance(extensions, str):
            extensions = [extensions]

        files_list = []
        root_folder_path = Path(root_folder).resolve()

        for root, _, files in os.walk(root_folder_path):
            for file in files:
                if any(file.lower().endswith(f".{ext}") for ext in extensions):
                    files_list.append(str(Path(root) / file))
        logger.info(f"Found {len(files_list)} files with extensions {extensions}")
        return files_list

    def store_output(self, data: Dict[str, Any], step: str) -> None:
        """
        Store the given data either in memory or in Cosmos DB.

        Args:
            data (Dict[str, Any]): The data to store.
            step (str): The step identifier to categorize the data.
        """
        data_to_store = {
            "case_id": self.case_id,
            "step": step,
            "data": data,
        }

        if self.local:
            if self.case_id not in self.conversation_history:
                self.conversation_history[self.case_id] = {}
            self.conversation_history[self.case_id][step] = data_to_store
        else:
            # Use CosmosDBManager to index data
            if self.cosmos_db_manager:
                self.cosmos_db_manager.index_data([data_to_store], id_key="case_id")
            else:
                logger.error("CosmosDBManager is not initialized.")

    def get_conversation_history(self) -> Dict[str, Any]:
        """
        Retrieve the conversation history.

        Returns:
            Dict[str, Any]: The conversation history dictionary.
        """
        if self.local:
            return self.conversation_history.get(self.case_id, {})
        else:
            if self.cosmos_db_manager:
                query = f"SELECT * FROM c WHERE c.case_id = '{self.case_id}'"
                results = self.cosmos_db_manager.execute_query(query)
                if results:
                    return {item["step"]: item["data"] for item in results}
                else:
                    return {}
            else:
                logger.error("CosmosDBManager is not initialized.")
                return {}

    async def process_documents_flow(self, input_dir: str) -> None:
        """
        Process documents as per the pipeline flow and store the outputs.

        Args:
            input_dir (str): Directory containing files to process.
        """
        uploaded_files = self.find_all_files(input_dir, ["pdf"])

        if uploaded_files:
            try:
                temp_dir = self.process_uploaded_files(uploaded_files)
                image_files = self.find_all_files(temp_dir, ["png"])

                # Generate AI response for NER
                logger.info(Fore.CYAN + "\nAnalyzing clinical information...")
                api_response_ner = await self.azure_openai_client.generate_chat_response(
                    query=USER_PROMPT_NER,
                    system_message_content=SYSTEM_PROMPT_NER,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=3000,
                )

                # Store NER response
                self.store_output(api_response_ner, step="NER_response")

                clinical_info = api_response_ner["response"].get("Clinical Information")
                if clinical_info:
                    prompt_query_expansion = create_prompt_query_expansion(clinical_info)
                    logger.info(
                        Fore.CYAN + "Expanding query and searching for policy..."
                    )
                    api_response_query = await self.azure_openai_client.generate_chat_response(
                    query=prompt_query_expansion,
                    system_message_content=SYSTEM_PROMPT_QUERY_EXPANSION,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=3000,)

                    # Store query expansion response
                    self.store_output(api_response_query, step="query_expansion")

                    # Locate the policy
                    policy_location = self.locate_policy(api_response_query)
                    if policy_location not in ["No results found", "Error locating policy"]:
                        policy_text = self.get_policy_text_from_blob(policy_location)

                        # Store policy text
                        self.store_output(
                            {
                                "policy_location": policy_location,
                                "policy_text": policy_text,
                            },
                            step="policy_retrieval",
                        )

                        if policy_text:
                            user_prompt_pa = create_prompt_pa(
                                clinical_info, policy_text
                            )
                            # Generate final AI response
                            logger.info(
                                Fore.CYAN + "Generating final determination..."
                            )
                            api_response_final = await self.generate_ai_response(
                                user_prompt_pa,
                                SYSTEM_PROMPT_PRIOR_AUTH,
                                image_files,
                            )
                            await self.azure_openai_client.generate_chat_response(
                                query=user_prompt_pa,
                                system_message_content=SYSTEM_PROMPT_PRIOR_AUTH,
                                conversation_history=[],
                                response_format="text",
                                max_tokens=3000,
                            )
                            final_response = api_response_final["response"]
                            logger.info(
                                Fore.MAGENTA
                                + "\nFinal Determination:\n"
                                + final_response
                            )

                            # Store final determination
                            self.store_output(
                                {"final_determination": final_response},
                                step="final_determination",
                            )
                        else:
                            logger.info(Fore.RED + "Policy text not found.")
                            self.store_output(
                                {"error": "Policy text not found."}, step="error"
                            )
                    else:
                        logger.info(Fore.RED + "Policy not found.")
                        self.store_output(
                            {"error": "Policy not found."}, step="error"
                        )
                else:
                    logger.info(
                        Fore.RED + "Clinical Information not found in AI response."
                    )
                    self.store_output(
                        {"error": "Clinical Information not found."}, step="error"
                    )
            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                self.store_output({"error": str(e)}, step="error")
        else:
            logger.info(Fore.RED + "No files found in the input directory.")

async def main():
    """
    Main function to run the application.

    This function initializes the processing pipeline and starts the document processing.
    """
    try:
        # Load configuration
        azure_openai_chat_deployment_id = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
        azure_ai_search_service_endpoint = os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT")
        azure_ai_search_index_name = os.getenv("AZURE_AI_SEARCH_INDEX_NAME")
        azure_ai_search_admin_key = os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
        azure_blob_container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
        cosmos_db_endpoint = os.getenv("AZURE_COSMOSDB_ENDPOINT")
        cosmos_db_key = os.getenv("AZURE_COSMOSDB_KEY")
        cosmos_db_database_name = os.getenv("AZURE_COSMOSDB_DATABASE")
        cosmos_db_container_name = os.getenv("AZURE_COSMOSDB_CONTAINER")

        # Determine if running in local or remote mode
        local_mode = True  # Set to True for local mode, False for remote mode

        # Initialize the processing pipeline
        pipeline = PAProcessingPipeline(
            azure_openai_chat_deployment_id=azure_openai_chat_deployment_id,
            azure_ai_search_service_endpoint=azure_ai_search_service_endpoint,
            azure_ai_search_index_name=azure_ai_search_index_name,
            azure_ai_search_admin_key=azure_ai_search_admin_key,
            azure_blob_container_name=azure_blob_container_name,
            local=local_mode,
            cosmos_db_endpoint=cosmos_db_endpoint,
            cosmos_db_key=cosmos_db_key,
            cosmos_db_database_name=cosmos_db_database_name,
            cosmos_db_container_name=cosmos_db_container_name,
        )

        # Ask the user for the directory of files to process
        input_dir = input(
            Fore.GREEN
            + "Enter the path to the directory containing files to process: "
        )

        # Process documents asynchronously
        await pipeline.process_documents_flow(input_dir)

        # Retrieve and display the conversation history
        conversation_history = pipeline.get_conversation_history()
        final_response = conversation_history.get("final_determination", {}).get("data", {}).get("final_determination")
        if final_response:
            print(
                Fore.MAGENTA + "\nFinal Determination:\n" + final_response
            )
        else:
            print(Fore.RED + "No final determination available.")

    except Exception as e:
        logger.error(f"Application encountered an error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
