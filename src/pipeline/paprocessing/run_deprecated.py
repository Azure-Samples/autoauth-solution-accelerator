import asyncio
import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Type, Union

import dotenv
import streamlit as st
import yaml
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from colorama import Fore, init
from opentelemetry import trace
from pydantic import BaseModel, ValidationError

from src.aoai.aoai_helper import AzureOpenAIManager
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.documentintelligence.document_intelligence_helper import (
    AzureDocumentIntelligenceManager,
)
from src.entraid.generate_id import generate_unique_id
from src.extractors.pdfhandler import OCRHelper
from src.pipeline.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.pipeline.paprocessing.utils import find_all_files
from src.pipeline.prompt_manager import PromptManager
from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger

init(autoreset=True)

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
        send_cloud_logs: bool = False,
    ):
        """
        Initialize the PAProcessingPipeline with provided parameters or environment variables.
        """
        with open(config_path, "r") as file:
            config = yaml.safe_load(file)

        azure_openai_chat_deployment_id = azure_openai_chat_deployment_id or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
        )
        azure_openai_key = azure_openai_key or os.getenv("AZURE_OPENAI_KEY")
        azure_search_service_endpoint = azure_search_service_endpoint or os.getenv(
            "AZURE_AI_SEARCH_SERVICE_ENDPOINT"
        )
        azure_search_index_name = azure_search_index_name or os.getenv(
            "AZURE_SEARCH_INDEX_NAME"
        )
        azure_search_admin_key = azure_search_admin_key or os.getenv(
            "AZURE_AI_SEARCH_ADMIN_KEY"
        )
        azure_blob_storage_account_name = azure_blob_storage_account_name or os.getenv(
            "AZURE_STORAGE_ACCOUNT_NAME"
        )
        azure_blob_storage_account_key = azure_blob_storage_account_key or os.getenv(
            "AZURE_STORAGE_ACCOUNT_KEY"
        )
        azure_cosmos_db_connection = azure_cosmos_db_connection or os.getenv(
            "AZURE_COSMOS_CONNECTION_STRING"
        )
        azure_cosmos_db_database_name = azure_cosmos_db_database_name or os.getenv(
            "AZURE_COSMOS_DB_DATABASE_NAME"
        )
        azure_cosmos_db_collection_name = azure_cosmos_db_collection_name or os.getenv(
            "AZURE_COSMOS_DB_COLLECTION_NAME"
        )
        azure_document_intelligence_endpoint = (
            azure_document_intelligence_endpoint
            or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        )
        azure_document_intelligence_key = azure_document_intelligence_key or os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_KEY"
        )

        self.azure_openai_client = AzureOpenAIManager(
            completion_model_name=azure_openai_chat_deployment_id,
            api_key=azure_openai_key,
        )
        self.azure_openai_client_o1 = AzureOpenAIManager(
            api_version=os.getenv("AZURE_OPENAI_API_VERSION_01") or "2024-09-01-preview"
        )
        self.search_client = SearchClient(
            endpoint=azure_search_service_endpoint,
            index_name=azure_search_index_name,
            credential=AzureKeyCredential(azure_search_admin_key),
        )
        self.container_name = config["remote_blob_paths"]["container_name"]
        self.remote_dir_base_path = config["remote_blob_paths"]["remote_dir_base"]
        self.raw_uploaded_files = config["remote_blob_paths"]["raw_uploaded_files"]
        self.processed_images = config["remote_blob_paths"]["processed_images"]
        self.caseId = caseId if caseId else generate_unique_id()
        self.azure_blob_storage_account_name = azure_blob_storage_account_name
        self.azure_blob_storage_account_key = azure_blob_storage_account_key
        # Azure OpenAI configuration
        self.temperature = config["azure_openai"]["temperature"]
        self.max_tokens = config["azure_openai"]["max_tokens"]
        self.top_p = config["azure_openai"]["top_p"]
        self.frequency_penalty = config["azure_openai"]["frequency_penalty"]
        self.presence_penalty = config["azure_openai"]["presence_penalty"]
        self.seed = config["azure_openai"]["seed"]

        self.document_intelligence_client = AzureDocumentIntelligenceManager(
            azure_endpoint=azure_document_intelligence_endpoint,
            azure_key=azure_document_intelligence_key,
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
        self.PATIENT_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt(
            "ner_patient_system.jinja"
        )
        self.PHYSICIAN_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt(
            "ner_physician_system.jinja"
        )
        self.CLINICIAN_PROMPT_NER_SYSTEM = self.prompt_manager.get_prompt(
            "ner_clinician_system.jinja"
        )
        self.PATIENT_PROMPT_NER_USER = self.prompt_manager.get_prompt(
            "ner_patient_user.jinja"
        )
        self.PHYSICIAN_PROMPT_NER_USER = self.prompt_manager.get_prompt(
            "ner_physician_user.jinja"
        )
        self.CLINICIAN_PROMPT_NER_USER = self.prompt_manager.get_prompt(
            "ner_clinician_user.jinja"
        )

        self.SYSTEM_PROMPT_QUERY_EXPANSION = self.prompt_manager.get_prompt(
            "query_expansion_system_prompt.jinja"
        )
        self.SYSTEM_PROMPT_PRIOR_AUTH = self.prompt_manager.get_prompt(
            "prior_auth_system_prompt.jinja"
        )

        self.SYSTEM_PROMPT_SUMMARIZE_POLICY = self.prompt_manager.get_prompt(
            "summarize_policy_system.jinja"
        )

        self.remote_dir = f"{self.remote_dir_base_path}/{self.caseId}"
        self.conversation_history: List[Dict[str, Any]] = []
        self.results: Dict[str, Any] = {}
        self.temp_dir = tempfile.mkdtemp()
        self.local = send_cloud_logs
        self.logger = get_logger(
            name="PAProcessing", level=10, tracing_enabled=self.local
        )

    def upload_files_to_blob(
        self, uploaded_files: Union[str, List[str]], step: str
    ) -> None:
        """
        Upload the given files to Azure Blob Storage.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]

        remote_files = []
        for file_path in uploaded_files:
            if os.path.isdir(file_path):
                self.logger.warning(
                    f"Skipping directory '{file_path}' as it cannot be uploaded as a file."
                )
                continue

            try:
                if file_path.startswith("http"):
                    blob_info = self.blob_manager._parse_blob_url(file_path)
                    destination_blob_path = (
                        f"{self.remote_dir}/{step}/{blob_info['blob_name']}"
                    )
                    self.blob_manager.copy_blob(file_path, destination_blob_path)
                    full_url = f"https://{self.azure_blob_storage_account_name}.blob.core.windows.net/{self.container_name}/{destination_blob_path}"
                    self.logger.info(
                        f"Copied blob from '{file_path}' to '{full_url}' in container '{self.blob_manager.container_name}'."
                    )
                    remote_files.append(full_url)
                else:
                    file_name = os.path.basename(file_path)
                    destination_blob_path = f"{self.remote_dir}/{step}/{file_name}"
                    self.blob_manager.upload_file(
                        file_path, destination_blob_path, overwrite=True
                    )
                    full_url = f"https://{self.azure_blob_storage_account_name}.blob.core.windows.net/{self.container_name}/{destination_blob_path}"
                    self.logger.info(
                        f"Uploaded file '{file_path}' to blob '{full_url}' in container '{self.blob_manager.container_name}'."
                    )
                    remote_files.append(full_url)
            except Exception as e:
                self.logger.error(f"Failed to upload or copy file '{file_path}': {e}")

        if self.caseId not in self.results:
            self.results[self.caseId] = {}
        self.results[self.caseId][step] = remote_files
        self.logger.info(
            f"All files processed for upload to Azure Blob Storage in container '{self.blob_manager.container_name}'."
        )

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
            # Initialize a local list for image files
            image_files = []
            for file_path in uploaded_files:
                self.logger.info(f"Processing file: {file_path}")
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=self.temp_dir
                )
                if not output_paths:
                    self.logger.warning(f"No images extracted from file '{file_path}'.")
                    continue

                # Upload each extracted image individually
                self.upload_files_to_blob(output_paths, step="processed_images")
                image_files.extend(output_paths)
                self.logger.info(f"Images extracted and uploaded from: {self.temp_dir}")

            self.logger.info(
                f"Files processed and images extracted to: {self.temp_dir}"
            )
            return self.temp_dir, image_files
        except Exception as e:
            self.logger.error(f"Failed to process files: {e}")
            return self.temp_dir, []

    def get_policy_text_from_blob(self, blob_url: str) -> str:
        """
        Download the blob content from the given URL and extract text.
        """
        try:
            # Download the blob content
            blob_content = self.blob_manager.download_blob_to_bytes(blob_url)
            if blob_content is None:
                raise Exception(f"Failed to download blob from URL: {blob_url}")
            self.logger.info(f"Blob content downloaded successfully from {blob_url}")

            # Analyze the document
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
                self.logger.error("CosmosDBManager is not initialized.")
                return {}

    def log_output(
        self,
        data: Dict[str, Any],
        conversation_history: List[str] = None,
        step: Optional[str] = None,
    ) -> None:
        """
        Store the given data either in memory or in Cosmos DB. Uses the caseId as a partition key.
        """
        try:
            if self.caseId not in self.results:
                self.results[self.caseId] = {}

            self.results[self.caseId].update(data)

            if conversation_history:
                self.conversation_history.append(conversation_history)

            self.logger.debug(f"Data logged for case '{self.caseId}' at step '{step}'.")
        except Exception as e:
            self.logger.error(
                f"Failed to log output for case '{self.caseId}', step '{step}': {e}"
            )

    def store_output(self) -> None:
        """
        Store the results into Cosmos DB, using the caseId as the unique identifier for upserts.
        """
        try:
            if self.cosmos_db_manager:
                case_data = self.results.get(self.caseId, {})
                if case_data:
                    data_item = case_data.copy()
                    data_item["caseId"] = self.caseId

                    query = {"caseId": self.caseId}

                    self.cosmos_db_manager.upsert_document(data_item, query)
                    self.logger.info(
                        f"Results stored in Cosmos DB for caseId {self.caseId}"
                    )
                else:
                    self.logger.warning(f"No results to store for caseId {self.caseId}")
            else:
                self.logger.error("CosmosDBManager is not initialized.")
        except Exception as e:
            self.logger.error(f"Failed to store results in Cosmos DB: {e}")

    def cleanup_temp_dir(self) -> None:
        """
        Cleans up the temporary directory used for processing files.
        """
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            self.logger.error(
                f"Failed to clean up temporary directory '{self.temp_dir}': {e}"
            )

    async def validate_with_field_level_correction(
        self, data: Dict[str, Any], model_class: Type[BaseModel]
    ) -> BaseModel:
        """
        Validate each field with a Pydantic model. Retain valid fields, correct invalid ones with defaults.
        """
        validated_data = {}

        for field_name, model_field in model_class.model_fields.items():
            # Get the field alias if it exists; otherwise, use the field name
            expected_alias = model_field.alias or field_name
            value = data.get(expected_alias, None)

            try:
                validated_instance = model_class(**{field_name: value})
                validated_data[field_name] = getattr(validated_instance, field_name)
            except ValidationError as e:
                self.logger.warning(f"Validation error for '{expected_alias}': {e}")

                if model_field.default is not None:
                    default_value = model_field.default
                elif model_field.default_factory is not None:
                    default_value = model_field.default_factory()
                else:
                    # Assign a default based on the type
                    field_type = model_field.outer_type_
                    if field_type == str:
                        default_value = "Not provided"
                    elif field_type == int:
                        default_value = 0
                    elif field_type == float:
                        default_value = 0.0
                    elif field_type == bool:
                        default_value = False
                    elif field_type == list:
                        default_value = []
                    elif field_type == dict:
                        default_value = {}
                    else:
                        default_value = None
                validated_data[field_name] = default_value

        try:
            instance = model_class(**validated_data)
        except ValidationError as e:
            self.logger.error(f"Failed to create {model_class.__name__} instance: {e}")
            raise

        return instance

    async def extract_patient_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract patient data using AI.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting patient data...")
            api_response_patient = (
                await self.azure_openai_client.generate_chat_response(
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
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_patient["response"], PatientInformation
            )
            self.log_output(
                validated_data.model_dump(mode="json"),
                api_response_patient["conversation_history"],
                step="patient_information_extraction",
            )
            return validated_data
        except Exception as e:
            self.logger.error(f"Error extracting patient data: {e}")
            return PatientInformation()

    async def extract_physician_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract physician data using AI.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting physician data...")
            api_response_physician = (
                await self.azure_openai_client.generate_chat_response(
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
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_physician["response"], PhysicianInformation
            )
            self.log_output(
                validated_data.model_dump(mode="json"),
                api_response_physician["conversation_history"],
                step="physician_information_extraction",
            )
            return validated_data
        except Exception as e:
            self.logger.error(f"Error extracting physician data: {e}")
            return PhysicianInformation()

    async def extract_clinician_data(self, image_files: List[str]) -> Dict[str, Any]:
        """
        Extract clinician data using AI.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting clinician data...")
            api_response_clinician = (
                await self.azure_openai_client.generate_chat_response(
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
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_clinician["response"], ClinicalInformation
            )
            self.log_output(
                validated_data.model_dump(mode="json"),
                api_response_clinician["conversation_history"],
                step="clinical_information_extraction",
            )
            return validated_data
        except Exception as e:
            self.logger.error(f"Error extracting clinician data: {e}")
            return ClinicalInformation()

    async def extract_all_data(self, image_files: List[str]) -> Dict[str, BaseModel]:
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
            self.logger.error(f"Error extracting all data: {e}")
            return {
                "patient_data": PatientInformation(),
                "physician_data": PhysicianInformation(),
                "clinician_data": ClinicalInformation(),
            }

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
                self.logger.warning("No results found")
                return "No results found"
        except Exception as e:
            self.logger.error(f"Error locating policy: {e}")
            return "Error locating policy"

    async def expand_query_and_search_policy(
        self, clinical_info: BaseModel
    ) -> Dict[str, Any]:
        """
        Expand query and search for policy.
        """
        prompt_query_expansion = self.prompt_manager.create_prompt_query_expansion(
            clinical_info
        )
        self.logger.info(Fore.CYAN + "Expanding query and searching for policy...")
        self.logger.info(f"Input clinical information: {clinical_info}")
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
        self.log_output(
            api_response_query["response"],
            api_response_query["conversation_history"],
            step="query_expansion",
        )
        self.logger.info(f"API response query: {api_response_query}")

        return api_response_query

    async def summarize_policy(self, policy_text: str) -> Dict[str, Any]:
        """
        Expand query and search for policy.
        """
        prompt_user_query_summary = self.prompt_manager.create_prompt_summary_policy(
            policy_text
        )
        self.logger.info(Fore.CYAN + "Summarizing Policy...")
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

        self.log_output(
            {"summary_policy": api_response_query["response"]},
            api_response_query["conversation_history"],
            step="summarize_policy",
        )
        self.logger.info(f"Summary policy: {api_response_query}")

        return api_response_query["response"]

    async def generate_final_determination(
        self,
        patient_info: BaseModel,
        physician_info: BaseModel,
        clinical_info: BaseModel,
        policy_text: str,
        use_o1: bool = False,
    ) -> None:
        """
        Generate final determination using AI.
        """
        user_prompt_pa = self.prompt_manager.create_prompt_pa(
            patient_info, physician_info, clinical_info, policy_text, use_o1
        )

        self.logger.info(
            Fore.CYAN + f"Generating final determination for {self.caseId or None}"
        )
        self.logger.info(f"Input clinical information: {user_prompt_pa}")

        async def generate_response_with_model(model_client, prompt, use_o1):
            try:
                api_response = await model_client.generate_chat_response_o1(
                    query=prompt,
                    conversation_history=[],
                    max_completion_tokens=15000,
                )
                if api_response == "maximum context length":
                    summarized_policy = await self.summarize_policy(policy_text)
                    summarized_prompt = self.prompt_manager.create_prompt_pa(
                        patient_info,
                        physician_info,
                        clinical_info,
                        summarized_policy,
                        use_o1,
                    )
                    api_response = await model_client.generate_chat_response_o1(
                        query=summarized_prompt,
                        conversation_history=[],
                        max_completion_tokens=15000,
                    )
                return api_response
            except Exception as e:
                self.logger.warning(
                    f"{model_client.__class__.__name__} model generation failed: {str(e)}"
                )
                raise e

        if use_o1:
            self.logger.info(
                Fore.CYAN
                + f"Using o1 model for final determination for {self.caseId or None}..."
            )
            try:
                api_response_determination = await generate_response_with_model(
                    self.azure_openai_client_o1, user_prompt_pa, use_o1
                )
            except Exception:
                self.logger.info(
                    Fore.CYAN
                    + f"Retrying with 4o model for final determination for {self.caseId or None}..."
                )
                use_o1 = False  # Fallback to 4o model

        if not use_o1:
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(
                        Fore.CYAN
                        + f"Using 4o model for final determination, attempt {attempt} for {self.caseId or None}..."
                    )
                    api_response_determination = (
                        await self.azure_openai_client.generate_chat_response(
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
                    )
                    if api_response_determination == "maximum context length":
                        summarized_policy = await self.summarize_policy(policy_text)
                        summarized_prompt = self.prompt_manager.create_prompt_pa(
                            patient_info,
                            physician_info,
                            clinical_info,
                            summarized_policy,
                            use_o1,
                        )
                        api_response_determination = (
                            await self.azure_openai_client.generate_chat_response(
                                query=summarized_prompt,
                                system_message_content=self.SYSTEM_PROMPT_PRIOR_AUTH,
                                conversation_history=[],
                                response_format="text",
                                max_tokens=self.max_tokens,
                                top_p=self.top_p,
                                temperature=self.temperature,
                                frequency_penalty=self.frequency_penalty,
                                presence_penalty=self.presence_penalty,
                            )
                        )
                    break
                except Exception as e:
                    self.logger.warning(
                        f"4o model generation failed on attempt {attempt}: {str(e)}"
                    )
                    if attempt < max_retries:
                        self.logger.info(
                            Fore.CYAN + "Retrying 4o model for final determination..."
                        )
                    else:
                        self.logger.error(
                            f"All retries for 4o model failed for {self.caseId or None}."
                        )
                        raise e

        final_response = api_response_determination["response"]
        self.logger.info(Fore.MAGENTA + "\nFinal Determination:\n" + final_response)
        self.log_output(
            {"final_determination": final_response},
            api_response_determination.get("conversation_history", []),
            step="llm_determination",
        )

    async def run(
        self,
        uploaded_files: List[str],
        streamlit: bool = False,
        caseId: str = None,
        use_o1: bool = False,
    ) -> None:
        """
        Process documents as per the pipeline flow and store the outputs.
        """
        dynamic_logger_name = f"Case_{caseId}" if caseId else "PaProcessing"

        if not uploaded_files:
            self.logger.info("No files provided for processing.")
            if streamlit:
                st.error("No files provided for processing.")
            return

        if caseId:
            self.caseId = caseId

        tracer = trace.get_tracer(dynamic_logger_name)
        start_time = time.time()
        with tracer.start_as_current_span(f"{dynamic_logger_name}.run") as span:
            span.set_attribute("caseId", self.caseId)
            span.set_attribute("uploaded_files", len(uploaded_files))
            self.logger.info(
                f"PAProcessing started {self.caseId}.",
                extra={"custom_dimensions": json.dumps({"caseId": self.caseId})},
            )
            try:
                temp_dir, image_files = self.process_uploaded_files(uploaded_files)
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

                clinical_info = api_response_ner.get("clinician_data")
                patient_info = api_response_ner.get("patient_data")
                physician_info = api_response_ner.get("physician_data")

                if streamlit:
                    status_text.write(
                        "🔎 **Expanding query and searching for policy...**"
                    )
                    progress += 1
                    progress_bar.progress(progress / total_steps)

                api_response_query = await self.expand_query_and_search_policy(
                    clinical_info
                )
                if api_response_query is None:
                    raise ValueError("Query expansion and search returned None")

                policy_location = self.locate_policy(api_response_query)
                if policy_location in ["No results found", "Error locating policy"]:
                    self.logger.info("Policy not found.")
                    if streamlit:
                        status_text.error("Policy not found.")
                        progress_bar.empty()
                    return

                policy_text = self.get_policy_text_from_blob(policy_location)
                if policy_text is None:
                    raise ValueError("Policy text extraction returned None")

                self.log_output(
                    data={
                        "policy_location": policy_location,
                        "policy_text": policy_text,
                    },
                    step="policy_extraction",
                )

                if streamlit:
                    status_text.write("📝 **Generating final determination...**")
                    progress += 1
                    progress_bar.progress(progress / total_steps)

                await self.generate_final_determination(
                    patient_info, physician_info, clinical_info, policy_text, use_o1
                )

                if streamlit:
                    end_time = time.time()  # End timing
                    execution_time = end_time - start_time
                    status_text.success(
                        f"✅ **PA {self.caseId} Processing completed in {execution_time:.2f} seconds!**"
                    )
                    progress_bar.progress(1.0)

            except Exception as e:
                self.logger.error(
                    f"PAprocessing failed for {self.caseId}: {e}",
                    extra={"custom_dimensions": json.dumps({"caseId": self.caseId})},
                )
                if streamlit:
                    st.error(f"PAprocessing failed for {self.caseId}: {e}")
            finally:
                self.cleanup_temp_dir()
                self.store_output()
                end_time = time.time()  # End timing
                execution_time = end_time - start_time
                self.logger.info(
                    f"PAprocessing completed for {self.caseId}. Execution time: {execution_time:.2f} seconds.",
                    extra={
                        "custom_dimensions": json.dumps(
                            {"caseId": self.caseId, "execution_time": execution_time}
                        )
                    },
                )
