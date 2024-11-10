import os
import yaml
import tempfile
import shutil
from typing import Any, Dict, List, Optional, Union

import dotenv
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from src.pipeline.paprocessing.helpers import find_all_files
from colorama import Fore, init
import asyncio
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.paprocessing.pdfhandler import OCRHelper
from src.documentintelligence.document_intelligence_helper import AzureDocumentIntelligenceManager
from src.entraid.generate_id import generate_unique_id
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.storage.blob_helper import AzureBlobManager
from src.pipeline.paprocessing.prompt_manager import PromptManager
from utils.ml_logging import get_logger

init(autoreset=True)
logger = get_logger()

dotenv.load_dotenv(".env")

import os
import yaml
import tempfile
import shutil
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
from src.pipeline.paprocessing.helpers import find_all_files
from colorama import Fore, init
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.paprocessing.pdfhandler import OCRHelper
from src.documentintelligence.document_intelligence_helper import AzureDocumentIntelligenceManager
from src.entraid.generate_id import generate_unique_id
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.storage.blob_helper import AzureBlobManager
from src.pipeline.paprocessing.prompt_manager import PromptManager
from utils.ml_logging import get_logger

init(autoreset=True)
logger = get_logger()

dotenv.load_dotenv(".env")

class PAProcessingPipeline:
    """
    A class to handle the Prior Authorization Processing Pipeline.
    """

    def __init__(
        self,
        caseId: Optional[str] = None,
        config_path: str = "src/pipeline/paprocessing/settings.yaml",
        azure_openai_chat_deployment_id: Optional[str] = None, 
        azure_openai_key: Optional[str] = None,
        azure_search_service_endpoint: Optional[str] = None,
        azure_search_index_name: Optional[str] = None,
        azure_search_admin_key: Optional[str] = None,
        azure_blob_storage_account_name: Optional[str] = None,
        azure_blob_storage_account_key: Optional[str] = None,
        azure_cosmos_db_connection: Optional[str] = None,
        azure_cosmos_db_database_name: Optional[str] = None,
        azure_cosmos_db_collection_name: Optional[str] = None,
        azure_document_intelligence_endpoint: Optional[str] = None,
        azure_document_intelligence_key: Optional[str] = None,
        local: bool = False,
    ):
        """
        Initialize the PAProcessingPipeline with provided parameters or environment variables.
        """
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)

        azure_openai_chat_deployment_id = azure_openai_chat_deployment_id or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
        azure_openai_key = azure_openai_key or os.getenv("AZURE_OPENAI_KEY")
        azure_search_service_endpoint = azure_search_service_endpoint or os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT")
        azure_search_index_name = azure_search_index_name or os.getenv("AZURE_SEARCH_INDEX_NAME")
        azure_search_admin_key = azure_search_admin_key or os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")
        azure_blob_storage_account_name = azure_blob_storage_account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        azure_blob_storage_account_key = azure_blob_storage_account_key or os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        azure_cosmos_db_connection = azure_cosmos_db_connection or os.getenv("AZURE_COSMOS_CONNECTION_STRING")
        azure_cosmos_db_database_name = azure_cosmos_db_database_name or os.getenv("AZURE_COSMOS_DB_DATABASE_NAME")
        azure_cosmos_db_collection_name = azure_cosmos_db_collection_name or os.getenv("AZURE_COSMOS_DB_COLLECTION_NAME")
        azure_document_intelligence_endpoint = azure_document_intelligence_endpoint or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        azure_document_intelligence_key = azure_document_intelligence_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        self.azure_openai_client = AzureOpenAIManager(
            completion_model_name=azure_openai_chat_deployment_id,
            api_key=azure_openai_key,
        )
        self.search_client = SearchClient(
            endpoint=azure_search_service_endpoint,
            index_name=azure_search_index_name,
            credential=AzureKeyCredential(azure_search_admin_key),
        )
        self.container_name = config['remote_blob_paths']['container_name']
        self.remote_dir_base_path = config['remote_blob_paths']['remote_dir_base']
        self.raw_uploaded_files = config['remote_blob_paths']['raw_uploaded_files']
        self.processed_images = config['remote_blob_paths']['processed_images']
        self.caseId = caseId if caseId else generate_unique_id()
        self.azure_blob_storage_account_name = azure_blob_storage_account_name
        self.azure_blob_storage_account_key = azure_blob_storage_account_key
        # Azure OpenAI configuration
        self.temperature = config['azure_openai']['temperature']
        self.max_tokens = config['azure_openai']['max_tokens']
        self.top_p = config['azure_openai']['top_p']
        self.frequency_penalty = config['azure_openai']['frequency_penalty']
        self.presence_penalty = config['azure_openai']['presence_penalty']
        self.seed = config['azure_openai']['seed']

        self.document_intelligence_client = AzureDocumentIntelligenceManager(
            azure_endpoint=azure_document_intelligence_endpoint,
            azure_key=azure_document_intelligence_key
        )
        self.blob_manager = AzureBlobManager(
            storage_account_name=self.azure_blob_storage_account_name,
            account_key=self.azure_blob_storage_account_key,
            container_name=self.container_name,
        )
        self.cosmos_db_manager = CosmosDBMongoCoreManager(
            connection_string=azure_cosmos_db_connection,
            database_name=azure_cosmos_db_database_name,
            collection_name=azure_cosmos_db_collection_name,
        )
        self.prompt_manager = PromptManager()
        self.PATIENT_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt('ner_patient_system.jinja')
        self.PHYSICIAN_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt('ner_physician_system.jinja')
        self.CLINICIAN_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt('ner_clinician_system.jinja')
        self.PATIENT_PROMPT_NER_USER = self.prompt_manager.get_prompt('ner_patient_user.jinja')
        self.PHYSICIAN_PROMPT_NER_USER = self.prompt_manager.get_prompt('ner_physician_user.jinja')
        self.CLINICIAN_PROMPT_NER_USER = self.prompt_manager.get_prompt('ner_clinician_user.jinja')

        self.SYSTEM_PROMPT_QUERY_EXPANSION = self.prompt_manager.get_prompt('query_expansion_system_prompt.jinja')
        self.SYSTEM_PROMPT_PRIOR_AUTH = self.prompt_manager.get_prompt('prior_auth_system_prompt.jinja')

        self.remote_dir = f"{self.remote_dir_base_path}/{self.caseId}"
        self.conversation_history: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {}
        self.temp_dir = tempfile.mkdtemp()
        self.local = local
                
    def upload_files_to_blob(self, uploaded_files: Union[str, List[str]], step: str) -> None:
        """
        Upload the given files to Azure Blob Storage.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]
    
        remote_files = []
        for file_path in uploaded_files:
            if os.path.isdir(file_path):
                logger.warning(f"Skipping directory '{file_path}' as it cannot be uploaded as a file.")
                continue
    
            try:
                if file_path.startswith("http"):
                    blob_info = self.blob_manager._parse_blob_url(file_path)
                    destination_blob_path = f"{self.remote_dir}/{step}/{blob_info['blob_name']}"
                    self.blob_manager.copy_blob(file_path, destination_blob_path)
                    full_url = f"https://{self.azure_blob_storage_account_name}.blob.core.windows.net/{self.container_name}/{destination_blob_path}"
                    logger.info(f"Copied blob from '{file_path}' to '{full_url}' in container '{self.blob_manager.container_name}'.")
                    remote_files.append(full_url)
                else:
                    file_name = os.path.basename(file_path)
                    destination_blob_path = f"{self.remote_dir}/{step}/{file_name}"
                    self.blob_manager.upload_file(file_path, destination_blob_path, overwrite=True)
                    full_url = f"https://{self.azure_blob_storage_account_name}.blob.core.windows.net/{self.container_name}/{destination_blob_path}"
                    logger.info(f"Uploaded file '{file_path}' to blob '{full_url}' in container '{self.blob_manager.container_name}'.")
                    remote_files.append(full_url)
            except Exception as e:
                logger.error(f"Failed to upload or copy file '{file_path}': {e}")

        if self.caseId not in self.results:
            self.results[self.caseId] = {}
        self.results[self.caseId][step] = remote_files
        logger.info(f"All files processed for upload to Azure Blob Storage in container '{self.blob_manager.container_name}'.")

    def process_uploaded_files(self, uploaded_files: Union[str, List[str]]) -> str:
        """
        Process uploaded files and extract images.
        """
        self.upload_files_to_blob(uploaded_files, step="raw_uploaded_files")
        ocr_helper = OCRHelper(
            storage_account_name=self.azure_blob_storage_account_name,
            container_name=self.container_name,
            account_key=self.azure_blob_storage_account_key,
        )
        try:
            for file_path in uploaded_files:
                logger.info(f"Processing file: {file_path}")
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=self.temp_dir
                )
                if not output_paths:
                    logger.warning(f"No images extracted from file '{file_path}'.")
                    continue

                # Upload each extracted image individually
                self.upload_files_to_blob(output_paths, step="processed_images")
                logger.info(f"Images extracted and uploaded from: {self.temp_dir}")

            logger.info(f"Files processed and images extracted to: {self.temp_dir}")
            return self.temp_dir
        except Exception as e:
            logger.error(f"Failed to process files: {e}")
            return self.temp_dir

    def get_policy_text_from_blob(self, blob_url: str) -> str:
        """
        Download the blob content from the given URL and extract text.
        """
        try:
            # Download the blob content
            blob_content = self.blob_manager.download_blob_to_bytes(blob_url)
            if blob_content is None:
                raise Exception(f"Failed to download blob from URL: {blob_url}")
            logger.info(f"Blob content downloaded successfully from {blob_url}")

            # Analyze the document
            policy_text = self.document_intelligence_client.analyze_document(
                document_input=blob_content,
                model_type="prebuilt-layout",
                output_format="markdown",
            )
            logger.info(f"Document analyzed successfully for blob {blob_url}")
            return policy_text.content
        except Exception as e:
            logger.error(f"Failed to get policy text from blob {blob_url}: {e}")
            return ""
    
    def get_conversation_history(self) -> Dict[str, Any]:
        """
        Retrieve the conversation history.
        """
        if self.local:
            return self.conversation_history
        else:
            if self.cosmos_db_manager:
                query = f"SELECT * FROM c WHERE c.caseId = '{self.caseId}'"
                results = self.cosmos_db_manager.execute_query(query)
                if results:
                    return {item["step"]: item["data"] for item in results}
                else:
                    return {}
            else:
                logger.error("CosmosDBManager is not initialized.")
                return {}

    def log_output(self, 
                   data: Dict[str, Any], 
                   conversation_history: List[str] = None, 
                   step: Optional[str] = None) -> None:
        """
        Store the given data either in memory or in Cosmos DB. Uses the caseId as a partition key.
        """
        try:
            if self.caseId not in self.results:
                self.results[self.caseId] = {}

            # Update the results dictionary based on the step
            if step is not None:
                self.results[self.caseId][step] = data
            else:
                self.results[self.caseId].update(data)

            if conversation_history:
                self.conversation_history.append(conversation_history)

            logger.info(f"Data logged for case '{self.caseId}' at step '{step}'.")
        except Exception as e:
            logger.error(f"Failed to log output for case '{self.caseId}', step '{step}': {e}")

    def store_output(self) -> None:
        """
        Store the results into Cosmos DB, using the caseId as the unique identifier for upserts.
        """
        try:
            if self.cosmos_db_manager:
                case_data = self.results.get(self.caseId, {})
                if case_data:
                    data_item = case_data.copy()
                    data_item['caseId'] = self.caseId

                    query = {"caseId": self.caseId}

                    self.cosmos_db_manager.upsert_document(data_item, query)
                    logger.info(f"Results stored in Cosmos DB for caseId {self.caseId}")
                else:
                    logger.warning(f"No results to store for caseId {self.caseId}")
            else:
                logger.error("CosmosDBManager is not initialized.")
        except Exception as e:
            logger.error(f"Failed to store results in Cosmos DB: {e}")


    def cleanup_temp_dir(self) -> None:
        """
        Cleans up the temporary directory used for processing files.
        """
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to clean up temporary directory '{self.temp_dir}': {e}")

    
    async def extract_patient_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract patient data using AI.
        """
        try:
            logger.info(Fore.CYAN + "\nExtracting patient data...")
            api_response_patient = await self.azure_openai_client.generate_chat_response(
                query=self.PATIENT_PROMPT_NER_USER,
                system_message_content=self.PATIENT_PROMPT_NER_SYSTEM,
                image_paths=image_files,
                conversation_history=[],
                response_format="json_object",
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                temperature=self.temperature,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
            )
            self.log_output(api_response_patient['response'], api_response_patient['conversation_history'])
            return api_response_patient['response']
        except Exception as e:
            logger.error(f"Error extracting patient data: {e}")
            return {"error": str(e)}

    async def extract_physician_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract physician data using AI.
        """
        try:
            logger.info(Fore.CYAN + "\nExtracting physician data...")
            api_response_physician = await self.azure_openai_client.generate_chat_response(
                query=self.PHYSICIAN_PROMPT_NER_USER,
                system_message_content=self.PHYSICIAN_PROMPT_NER_SYSTEM,
                image_paths=image_files,
                conversation_history=[],
                response_format="json_object",
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                temperature=self.temperature,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
            )
            self.log_output(api_response_physician['response'], api_response_physician['conversation_history'])
            return api_response_physician['response']
        except Exception as e:
            logger.error(f"Error extracting physician data: {e}")
            return {"error": str(e)}

    async def extract_clinician_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract clinician data using AI.
        """
        try:
            logger.info(Fore.CYAN + "\nExtracting clinician data...")
            api_response_clinician = await self.azure_openai_client.generate_chat_response(
                query=self.CLINICIAN_PROMPT_NER_USER,
                system_message_content=self.CLINICIAN_PROMPT_NER_SYSTEM,
                image_paths=image_files,
                conversation_history=[],
                response_format="json_object",
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                temperature=self.temperature,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
            )
            self.log_output(api_response_clinician['response'], api_response_clinician['conversation_history'])
            return api_response_clinician['response']
        except Exception as e:
            logger.error(f"Error extracting clinician data: {e}")
            return {"error": str(e)}

    async def extract_all_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract patient, physician, and clinician data in parallel.
        """
        try:
            patient_data_task = self.extract_patient_data(image_files)
            physician_data_task = self.extract_physician_data(image_files)
            clinician_data_task = self.extract_clinician_data(image_files)

            patient_data, physician_data, clinician_data = await asyncio.gather(
                patient_data_task, physician_data_task, clinician_data_task
            )
            return {
                "patient_data": patient_data,
                "physician_data": physician_data,
                "clinician_data": clinician_data,
            }
        except Exception as e:
            logger.error(f"Error extracting all data: {e}")
            return {"error": str(e)}

    def locate_policy(self, api_response: Dict[str, Any]) -> str:
        """
        Locate the policy based on the optimized query from the AI response.
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
                logger.warning("No results found")
                return "No results found"
        except Exception as e:
            logger.error(f"Error locating policy: {e}")
            return "Error locating policy"
                    
    async def analyze_clinical_information(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Analyze clinical information using AI.
        """
        logger.info(Fore.CYAN + "\nAnalyzing clinical information...")
        api_response_ner = await self.azure_openai_client.generate_chat_response(
            query=self.USER_PROMPT_NER,
            system_message_content=self.SYSTEM_PROMPT_NER,
            image_paths=image_files,
            conversation_history=[],
            response_format="json_object",
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        self.log_output(api_response_ner['response'], api_response_ner['conversation_history'], step=None)
        return api_response_ner

    async def expand_query_and_search_policy(self, clinical_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand query and search for policy.
        """
        prompt_query_expansion = self.prompt_manager.create_prompt_query_expansion(clinical_info)
        logger.info(Fore.CYAN + "Expanding query and searching for policy...")
        logger.info(f"Input clinical information: {clinical_info}")
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

        # Store query expansion response
        self.log_output(api_response_query['response'], api_response_query['conversation_history'], step=None)
        logger.info(f"API response query: {api_response_query}")
        
        return api_response_query

    async def generate_final_determination(self, retrieved_infromation_ner: Dict[str, Any], policy_text: str) -> None:
        """
        Generate final determination using AI.
        """
        user_prompt_pa = self.prompt_manager.create_prompt_pa(retrieved_infromation_ner, policy_text)
        print(user_prompt_pa)
        logger.info(Fore.CYAN + "Generating final determination...")
        logger.info(f"Input clinical information: {user_prompt_pa}")
        api_response_determination = await self.azure_openai_client.generate_chat_response(
            query=user_prompt_pa,
            system_message_content=self.SYSTEM_PROMPT_PRIOR_AUTH,
            conversation_history=[],
            response_format="text",
            max_tokens=self.max_tokens,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        final_response = api_response_determination["response"]
        logger.info(Fore.MAGENTA + "\nFinal Determination:\n" + final_response)
        self.log_output({"final_determination": final_response}, api_response_determination['conversation_history'], step=None)

    async def run(self, uploaded_files: List[str], streamlit: bool = False, caseId: str = None) -> None:
        """
        Process documents as per the pipeline flow and store the outputs.
        """
        if not uploaded_files:
            logger.info(Fore.RED + "No files provided for processing.")
            if streamlit:
                st.error("No files provided for processing.")
            return
        if caseId: 
            self.caseId = caseId
        try:
            temp_dir = self.process_uploaded_files(uploaded_files)
            image_files = find_all_files(temp_dir, ["png"])

            if streamlit:
                progress_bar = st.progress(0)
                status_text = st.empty()
                progress = 0
                total_steps = 4

                status_text.write("🔍 **Analyzing clinical information...**")
                progress += 1
                progress_bar.progress(progress / total_steps)

            api_response_ner = await self.extract_all_data(image_files)
            clinical_info = api_response_ner["clinician_data"]

            if not clinical_info:
                logger.info(Fore.RED + "Clinical Information not found in AI response.")
                if streamlit:
                    status_text.error("Clinical Information not found in AI response.")
                    progress_bar.empty()
                return

            if streamlit:
                status_text.write("🔎 **Expanding query and searching for policy...**")
                progress += 1
                progress_bar.progress(progress / total_steps)

            api_response_query = await self.expand_query_and_search_policy(clinical_info)
            policy_location = self.locate_policy(api_response_query)

            if policy_location in ["No results found", "Error locating policy"]:
                logger.info(Fore.RED + "Policy not found.")
                if streamlit:
                    status_text.error("Policy not found.")
                    progress_bar.empty()
                return

            policy_text = self.get_policy_text_from_blob(policy_location)

            if not policy_text:
                logger.info(Fore.RED + "Policy text not found.")
                if streamlit:
                    status_text.error("Policy text not found.")
                    progress_bar.empty()
                return

            self.log_output(
                {
                    "policy_location": policy_location,
                    "policy_text": policy_text,
                }
            )

            if streamlit:
                status_text.write("📝 **Generating final determination...**")
                progress += 1
                progress_bar.progress(progress / total_steps)

            await self.generate_final_determination(api_response_ner, policy_text)

            if streamlit:
                status_text.success(f"✅ **PA {self.caseId} Processing complete!**")
                progress_bar.progress(1.0)

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            if streamlit:
                st.error(f"Document processing failed: {e}")
        finally:
            self.cleanup_temp_dir()
            self.store_output()
