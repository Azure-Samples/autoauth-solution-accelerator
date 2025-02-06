# main_pipeline.py
import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Union

import dotenv
import streamlit as st
import yaml
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from colorama import Fore, init
from opentelemetry import trace

from src.aoai.aoai_helper import AzureOpenAIManager
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.documentintelligence.document_intelligence_helper import (
    AzureDocumentIntelligenceManager,
)
from src.entraid.generate_id import generate_unique_id
from src.extractors.pdfhandler import OCRHelper
from src.pipeline.agenticRag.run import AgenticRAG
from src.pipeline.autoDetermination.run import AutoPADeterminator
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.paprocessing.utils import find_all_files
from src.pipeline.promptEngineering.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.pipeline.promptEngineering.prompt_manager import PromptManager
from src.storage.blob_helper import AzureBlobManager
from src.utils.ml_logging import get_logger

init(autoreset=True)
dotenv.load_dotenv(".env")


class PAProcessingPipeline:
    """
    Orchestrates the Prior Authorization Processing Pipeline, coordinating:
    - File upload and image extraction
    - Clinical data extraction
    - Query expansion and policy retrieval
    - Final determination generation

    All logic and method signatures remain unchanged from original code.
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
    ) -> None:
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
        if azure_search_admin_key is None:
            self.search_client = SearchClient(
                endpoint=azure_search_service_endpoint,
                index_name=azure_search_index_name,
                credential=DefaultAzureCredential(),
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

        self.temperature = config["azure_openai"]["temperature"]
        self.max_tokens = config["azure_openai"]["max_tokens"]
        self.top_p = config["azure_openai"]["top_p"]
        self.frequency_penalty = config["azure_openai"]["frequency_penalty"]
        self.presence_penalty = config["azure_openai"]["presence_penalty"]
        self.seed = config["azure_openai"]["seed"]

        self.document_intelligence_client = AzureDocumentIntelligenceManager(
            azure_endpoint=azure_document_intelligence_endpoint,
            azure_key=azure_document_intelligence_key,
            storage_account_name=azure_blob_storage_account_name,
            container_name=self.container_name,
            account_key=azure_blob_storage_account_key,
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

        # Prompts loaded exactly as originally implemented, no logic changes
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

        # Initialize helper classes with all parameters exactly as before
        self.clinical_data_extractor = ClinicalDataExtractor(
            azure_openai_client=self.azure_openai_client,
            prompt_manager=self.prompt_manager,
            caseId=self.caseId,
        )

        self.agentic_rag = AgenticRAG(
            azure_openai_client=self.azure_openai_client,
            prompt_manager=self.prompt_manager,
            search_client=self.search_client,
            azure_blob_manager=self.blob_manager,
            document_intelligence_client=self.document_intelligence_client,
            caseId=self.caseId,
        )

        self.auto_pa_determinator = AutoPADeterminator(
            azure_openai_client=self.azure_openai_client,
            azure_openai_client_o1=self.azure_openai_client_o1,
            prompt_manager=self.prompt_manager,
            caseId=self.caseId,
        )

    def upload_files_to_blob(
        self, uploaded_files: Union[str, List[str]], step: str
    ) -> None:
        """
        Upload the given files to Azure Blob Storage.

        Args:
            uploaded_files: A file path or list of file paths to upload.
            step: The current step or directory name to store these files under.
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

    def process_uploaded_files(
        self, uploaded_files: Union[str, List[str]]
    ) -> Union[str, List[str]]:
        """
        Process uploaded files and extract images.

        Args:
            uploaded_files: A file path or list of file paths representing the uploaded PDFs.

        Returns:
            A tuple containing the temporary directory path and the list of extracted image file paths.
        """
        self.upload_files_to_blob(uploaded_files, step="raw_uploaded_files")
        ocr_helper = OCRHelper(
            storage_account_name=self.azure_blob_storage_account_name,
            container_name=self.container_name,
            account_key=self.azure_blob_storage_account_key,
        )
        try:
            image_files: List[str] = []
            for file_path in uploaded_files:
                self.logger.info(f"Processing file: {file_path}")
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=self.temp_dir
                )
                if not output_paths:
                    self.logger.warning(f"No images extracted from file '{file_path}'.")
                    continue

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
        Retrieve policy text from the specified blob URL using Document Intelligence.

        Args:
            blob_url: The URL to the policy blob.

        Returns:
            The text content of the downloaded policy document.
        """
        try:
            # blob_content = self.blob_manager.download_blob_to_bytes(blob_url)
            # if blob_content is None:
            #     raise Exception(f"Failed to download blob from URL: {blob_url}")
            # self.logger.info(f"Blob content downloaded successfully from {blob_url}")

            policy_text = self.document_intelligence_client.analyze_document(
                # document_input=blob_content,
                document_input=blob_url,
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
        Retrieve the conversation history for this case.

        Returns:
            A dictionary representing the conversation history retrieved from memory or CosmosDB.
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

        Args:
            data: A dictionary of results to store.
            conversation_history: The conversation history associated with this step.
            step: The step or stage of the pipeline.
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

    async def summarize_policy(self, policy_text: str) -> str:
        """
        Summarize a given policy text using the LLM.

        Args:
            policy_text: The full text of the policy document.

        Returns:
            A summarized version of the policy text.
        """
        self.logger.info(Fore.CYAN + "Summarizing Policy...")
        system_message_content = self.prompt_manager.get_prompt(
            "summarize_policy_system.jinja"
        )
        prompt_user_query_summary = self.prompt_manager.create_prompt_summary_policy(
            policy_text
        )
        api_response_query = await self.azure_openai_client.generate_chat_response(
            query=prompt_user_query_summary,
            system_message_content=system_message_content,
            conversation_history=[],
            response_format="text",
            max_tokens=4096,
            top_p=self.top_p,
            temperature=self.temperature,
            frequency_penalty=self.frequency_penalty,
            presence_penalty=self.presence_penalty,
        )
        return api_response_query["response"]

    async def run(
        self,
        uploaded_files: List[str],
        streamlit: bool = False,
        caseId: str = None,
        use_o1: bool = False,
    ) -> None:
        """
        Process documents as per the pipeline flow and store the outputs.

        Steps:
        1. Process and extract images from uploaded PDF files.
        2. Extract patient, physician, and clinical data.
        3. Expand query and search for relevant policy.
        4. Retrieve and possibly summarize policy.
        5. Generate final determination.
        6. Store and log results.

        Args:
            uploaded_files: A list of PDF file paths to process.
            streamlit: Whether to update a Streamlit UI during processing.
            caseId: Optional case ID.
            use_o1: Whether to attempt using O1 model first for final determination.
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

                api_response_ner = await self.clinical_data_extractor.run(
                    image_files,
                    PatientInformation,
                    PhysicianInformation,
                    ClinicalInformation,
                )

                clinical_info = api_response_ner.get("clinician_data")
                patient_info = api_response_ner.get("patient_data")
                physician_info = api_response_ner.get("physician_data")

                self.log_output(
                    data={
                        "ocr_ner_results": {
                            "patient_info": patient_info.model_dump(mode="json"),
                            "physician_info": physician_info.model_dump(mode="json"),
                            "clinical_info": clinical_info.model_dump(mode="json"),
                        },
                    },
                    step="ocr_ner_extraction",
                )

                if streamlit:
                    status_text.write(
                        "🔎 **Expanding query and searching for policy...**"
                    )
                    progress += 1
                    progress_bar.progress(progress / total_steps)

                agenticrag_results = await self.agentic_rag.run(
                    clinical_info, max_retries=3
                )
                policies = agenticrag_results.get("policies", [])

                if not policies:
                    raise ValueError(
                        "No policies found for the given clinical information"
                    )

                # TODO: Currently deterministically choosing the top 1 result. Improve this logic based on the use case.
                policy_texts = []
                policy_text = None
                if policies:
                    policy = policies[0]
                    policy_text = self.get_policy_text_from_blob(policy)
                    if policy_text is None:
                        raise ValueError(
                            f"Policy text extraction returned None for policy: {policy}"
                        )
                    policy_texts.append(policy_text)
                else:
                    raise ValueError(
                        "No policies found for the given clinical information"
                    )

                self.log_output(
                    data={
                        "agenticrag_results": agenticrag_results,
                    },
                    step="policy_search",
                )

                async def summarize_policy_callback(text: str) -> str:
                    summary = await self.summarize_policy(text)
                    self.log_output(
                        {"summary_policy": summary}, [], step="summarize_policy"
                    )
                    return summary

                if streamlit:
                    status_text.write("📝 **Generating final determination...**")
                    progress += 1
                    progress_bar.progress(progress / total_steps)

                (
                    final_determination,
                    final_conv_history,
                ) = await self.auto_pa_determinator.run(
                    caseId=self.caseId,
                    patient_info=patient_info,
                    physician_info=physician_info,
                    clinical_info=clinical_info,
                    policy_text=policy_text,
                    summarize_policy_callback=summarize_policy_callback,
                    use_o1=use_o1,
                )

                self.log_output(
                    {"pa_determination_results": final_determination},
                    final_conv_history,
                    step="llm_determination",
                )

                if streamlit:
                    end_time = time.time()
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
                end_time = time.time()
                execution_time = end_time - start_time
                self.logger.info(
                    f"PAprocessing completed for {self.caseId}. Execution time: {execution_time:.2f} seconds.",
                    extra={
                        "custom_dimensions": json.dumps(
                            {"caseId": self.caseId, "execution_time": execution_time}
                        )
                    },
                )
