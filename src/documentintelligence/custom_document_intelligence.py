# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

# Inspired by the excellent work from Szeting Lau's Custom Classifier project:
# https://github.com/szetinglau/CustomClassifier/blob/main/build_classifier.py


import json
import logging
import os
import uuid
import mimetypes
from azure.core.exceptions import HttpResponseError
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

from azure.ai.documentintelligence import (
    DocumentIntelligenceAdministrationClient,
    DocumentIntelligenceClient,
)
from azure.ai.documentintelligence.models import (
    AnalyzeResult,
    AzureBlobFileListContentSource,
    BuildDocumentClassifierRequest,
    ClassifierDocumentTypeDetails,
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import HttpResponseError
from azure.storage.blob import (
    BlobClient,
    BlobServiceClient,
    ContainerClient,
    ContainerSasPermissions,
    generate_container_sas,
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import logging
import os

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient


class DocumentIntelligenceCustomPipeline:
    def __init__(
        self,
        endpoint: str = None,
        key: str = None,
        local_directory: Optional[str] = None,
        connect_str: str = None,
        container_name: str = None,
    ):
        """
        Initialize the DocumentProcessingPipeline with necessary configurations and clients.

        Parameters:
        endpoint (str): The endpoint for the Azure Document Intelligence service.
        key (str): The key for the Azure Document Intelligence service.
        local_directory (str): The local directory containing training documents.
        connect_str (str): The connection string for Azure Storage.
        container_name (str): The name of the Azure Storage container.
        """
        try:
            self.endpoint = (
                endpoint or os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
            )
            self.key = key or os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"]
            self.local_directory = local_directory
            self.connect_str = (
                connect_str or os.environ["AZURE_STORAGE_CONNECTION_STRING"]
            )
            self.container_name = (
                container_name or os.environ["AZURE_STORAGE_CONTAINER_NAME"]
            )

            self.document_intelligence_client = DocumentIntelligenceClient(
                endpoint=self.endpoint, credential=AzureKeyCredential(self.key)
            )
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connect_str
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )

            if not self.container_client.exists():
                logger.info(
                    f"Container {self.container_name} does not exist. Creating container..."
                )
                self.container_client.create_container()
                logger.info(f"Container {self.container_name} created!")
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            raise

    def analyze_layout(
        self,
        local_directory: Optional[str] = None,
        max_workers: Optional[int] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Analyzes documents in the specified directory and creates .ocr.json files.

        :param local_directory: Optional path to the directory containing documents to be analyzed.
        :param max_workers: Optional number of threads to use for parallel processing.
        :param restart: Boolean flag to skip files that already contain .ocr.json file if False.
        """
        local_directory = local_directory or self.local_directory
        incompatible_files: List[str] = []

        def analyze_document(file_path: str) -> None:
            """
            Analyzes a single document and creates an OCR JSON file.

            :param file_path: Path to the document file.
            """
            ocr_json_file_path = file_path + ".ocr.json"
            if not overwrite and os.path.exists(ocr_json_file_path):
                logger.info(f"Skipping {file_path} as .ocr.json file already exists")
                return

            try:
                with open(file_path, "rb") as f:
                    poller = self.document_intelligence_client.begin_analyze_document(
                        "prebuilt-layout",
                        analyze_request=f,
                        content_type="application/octet-stream",
                        cls=lambda raw_response, _, headers: self.create_ocr_json(
                            ocr_json_file_path, raw_response
                        ),
                    )
                    poller.result()
                logger.info(f"Analyzed document in {file_path}")
            except HttpResponseError as error:
                logger.error(
                    f"Analysis of {file_path} failed: {error.error}\n\nSkipping to next file..."
                )
                incompatible_files.append(file_path)
            except Exception as e:
                logger.error(f"Unexpected error during analysis of {file_path}: {e}")
                incompatible_files.append(file_path)

        def is_valid_file(file_path: str) -> bool:
            """
            Validates that the file is of a supported format.

            :param file_path: Path to the file to validate.
            :return: True if the file is valid, False otherwise.
            """
            valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heif")
            return file_path.lower().endswith(valid_extensions)

        def collect_files(directory: str, overwrite: bool = False) -> List[str]:
            """
            Collects all valid document files from the specified directory and its subdirectories.

            :param directory: The directory to search for document files.
            :param overwrite: Whether to overwrite existing .ocr.json files.
            :return: A list of paths to the document files.
            """
            files_to_analyze = []
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    if is_valid_file(file_path):
                        ocr_json_file_path = f"{file_path}.ocr.json"
                        if not overwrite and os.path.exists(ocr_json_file_path):
                            continue
                        files_to_analyze.append(file_path)

            logger.info(
                f"Collected {len(files_to_analyze)} documents for analysis and generation."
            )
            return files_to_analyze

        files_to_analyze = collect_files(local_directory, overwrite)

        if not files_to_analyze:
            logger.info("No documents to analyze. Exiting.")
            return

        with ThreadPoolExecutor(max_workers=max_workers or os.cpu_count()) as executor:
            futures = [
                executor.submit(analyze_document, file_path)
                for file_path in files_to_analyze
            ]

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"An error occurred during document analysis: {e}")

        if incompatible_files:
            logger.info(
                "\nThe following files were skipped as they are corrupted or the format is unsupported:"
            )
            for file in incompatible_files:
                logger.info(f"\t{file}")
            logger.info(
                "Please visit the following link for more information on supported file types and sizes. \nhttps://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-custom-classifier?view=doc-intel-4.0.0#input-requirements"
            )

        logger.info("Batch layout analysis completed!")

    def create_ocr_json(self, ocr_json_file_path: str, raw_response: Any) -> None:
        """
        Creates .ocr.json file from the raw response.

        :param ocr_json_file_path: Path to save the OCR JSON file.
        :param raw_response: Raw response from the document analysis.
        """
        try:
            with open(ocr_json_file_path, "w", encoding="utf-8") as f:
                f.write(raw_response.http_response.body().decode("utf-8"))
                logger.info(f"\tOutput saved to {ocr_json_file_path}")
        except Exception as e:
            logger.error(f"Failed to create OCR JSON file at {ocr_json_file_path}: {e}")
            raise

    def upload_file_to_blob(
        self, local_file_path: str, jsonl_data: Optional[List[Dict[str, str]]] = None
    ) -> None:
        """
        Uploads a single file to Azure Blob Storage.

        :param local_file_path: Path of the local file to upload.
        :param jsonl_data: Optional list to append JSONL data.
        """
        try:
            blob_name = os.path.relpath(local_file_path, self.local_directory).replace(
                "\\", "/"
            )
            if jsonl_data is not None:
                jsonl_data.append({"file": f"{blob_name}"})
            blob_client = self.container_client.get_blob_client(blob_name)
            with open(local_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
            logger.info(
                f"Uploaded {local_file_path} to {blob_name} in container {self.container_name}"
            )
        except Exception as e:
            logger.error(f"Failed to upload file {local_file_path} to blob: {e}")
            raise
    
    def build_classifier(
            self,
            base_classifier_id: Optional[str] = None,
            classifier_description: Optional[str] = None,
        ) -> None:
        """
        Builds a classifier model using the uploaded documents.
    
        :param base_classifier_id: Base classifier ID for incremental training.
        :param classifier_description: Description of the classifier.
        """
        try:
            document_model_admin_client, container_client = self.create_clients()
            container_sas_url = self.create_container_sas_url(container_client)
    
            poller = document_model_admin_client.begin_build_classifier(
                BuildDocumentClassifierRequest(
                    classifier_id=str(uuid.uuid4()),
                    base_classifier_id=base_classifier_id,
                    description=classifier_description,
                    doc_types=self.get_doctypes(container_client, container_sas_url),
                )
            )
            result = poller.result()
            self.print_classifier_results(result)
        except HttpResponseError as e:
            logger.error(f"Failed to build classifier: {e}")
            if hasattr(e, 'error') and e.error:
                logger.error(f"Error Code: {e.error.code}")
                logger.error(f"Error Message: {e.error.message}")
                if hasattr(e.error, 'inner_error') and e.error.inner_error:
                    logger.error(f"Inner Error Code: {e.error.inner_error.code}")
                    logger.error(f"Inner Error Message: {e.error.inner_error.message}")
            raise
        except Exception as e:
            logger.error(f"Failed to build classifier: {e}")
            raise

    def create_clients(
        self,
    ) -> Tuple[DocumentIntelligenceAdministrationClient, ContainerClient]:
        """
        Creates necessary clients for building the classifier.

        :return: A tuple containing the DocumentIntelligenceAdministrationClient and the ContainerClient.
        """
        try:
            document_model_admin_client = DocumentIntelligenceAdministrationClient(
                endpoint=self.endpoint, credential=AzureKeyCredential(self.key)
            )
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            return document_model_admin_client, container_client
        except Exception as e:
            logger.error(f"Failed to create clients: {e}")
            raise

    def get_doctypes(
        self, container_client: ContainerClient, container_sas_url: str
    ) -> Dict[str, ClassifierDocumentTypeDetails]:
        """
        Retrieves document types from the container.

        :param container_client: The ContainerClient to interact with the container.
        :param container_sas_url: The SAS URL for the container.
        :return: A dictionary of document types and their details.
        """
        try:
            doc_types: Dict[str, ClassifierDocumentTypeDetails] = {}
            doc_types_list: List[str] = []

            blob_list = container_client.walk_blobs()
            for blob in blob_list:
                if blob.name.endswith(".jsonl"):
                    doc_type = os.path.splitext(blob.name)[0]
                    doc_types_list.append(doc_type)

            for doc_type in doc_types_list:
                doc_types[doc_type] = ClassifierDocumentTypeDetails(
                    azure_blob_file_list_source=AzureBlobFileListContentSource(
                        container_url=container_sas_url, file_list=f"{doc_type}.jsonl"
                    )
                )
            return doc_types
        except Exception as e:
            logger.error(f"Failed to retrieve document types: {e}")
            raise

    def create_container_sas_url(self, container_client: ContainerClient) -> str:
        """
        Creates a SAS URL for the container.

        :param container_client: The ContainerClient to interact with the container.
        :return: The SAS URL for the container.
        """
        try:
            sas_permissions = ContainerSasPermissions(read=True, list=True)
            start_time = datetime.now(timezone.utc) - timedelta(minutes=1)
            expiry_time = datetime.now(timezone.utc) + timedelta(minutes=5)
            container_sas_token = generate_container_sas(
                container_client.account_name,
                container_client.container_name,
                account_key=container_client.credential.account_key,
                permission=sas_permissions,
                expiry=expiry_time,
                start=start_time,
            )
            container_sas_url = f"{container_client.url}?{container_sas_token}"
            return container_sas_url
        except Exception as e:
            logger.error(f"Failed to create container SAS URL: {e}")
            raise

    def upload_documents(self, local_directory: Optional[str] = None, max_workers: Optional[int] = None) -> None:
        """
        Uploads labeled data to Azure Blob Storage.
        
        :param local_directory: Optional path to the directory containing documents to be uploaded.
        :param max_workers: Optional number of threads to use for parallel processing.
        """
        local_directory = local_directory or self.local_directory
        incompatible_files: List[str] = []

        def upload_file(local_file_path: str, jsonl_data: Optional[List[Dict[str, str]]] = None) -> None:
            """
            Uploads a single file to Azure Blob Storage.
            
            :param local_file_path: Path of the local file to upload.
            :param jsonl_data: Optional list to append JSONL data.
            """
            try:
                blob_name = os.path.relpath(local_file_path, self.local_directory).replace("\\", "/")
                if jsonl_data is not None:
                    jsonl_data.append({"file": f"{blob_name}"})
                blob_client = self.container_client.get_blob_client(blob_name)
                with open(local_file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
                logger.info(f"Uploaded {local_file_path} to {blob_name} in container {self.container_name}")
            except Exception as e:
                logger.error(f"Failed to upload file {local_file_path} to blob: {e}")

        def collect_files(directory: str) -> List[str]:
            """
            Collects all valid document files from the specified directory and its subdirectories.
            
            :param directory: The directory to search for document files.
            :return: A list of paths to the document files.
            """
            files_to_upload = []
            for root, dirs, files in os.walk(directory):
                for dir in dirs:
                    jsonl_data = []
                    dir_path = os.path.join(root, dir)
                    for file in os.listdir(dir_path):
                        local_file_path = os.path.join(dir_path, file)
                        ocr_json_file_path = local_file_path + ".ocr.json"
                        if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".heif", ".pdf", ".docx", ".xlsx", ".pptx")):
                            if os.path.isfile(ocr_json_file_path):
                                files_to_upload.append(local_file_path)
                                files_to_upload.append(ocr_json_file_path)
                                jsonl_data.append({"file": os.path.relpath(local_file_path, self.local_directory).replace("\\", "/")})
                            else:
                                incompatible_files.append(local_file_path)
                        elif not file.endswith((".ocr.json", ".jsonl")):
                            incompatible_files.append(local_file_path)

                    # Write the .jsonl file as long as there are at least 5 training files per document type
                    if len(jsonl_data) >= 5:
                        jsonl_file_path = os.path.join(local_directory, f"{dir}.jsonl")
                        with open(jsonl_file_path, "w") as f:
                            for item in jsonl_data:
                                f.write(json.dumps(item) + "\n")
                        files_to_upload.append(jsonl_file_path)
            return files_to_upload

        files_to_upload = collect_files(local_directory)
        total_files = len(files_to_upload)
        if not files_to_upload:
            logger.info("No documents to upload. Exiting.")
            return

        logger.info(f"Starting upload of {total_files} files...")

        upload_count = 0
        with ThreadPoolExecutor(max_workers=max_workers or os.cpu_count()) as executor:
            futures = {executor.submit(upload_file, file_path): file_path for file_path in files_to_upload}

            for future in as_completed(futures):
                try:
                    future.result()
                    upload_count += 1
                    logger.info(f"Uploaded {upload_count}/{total_files} files.")
                except Exception as e:
                    logger.error(f"An error occurred during file upload: {e}")

        if incompatible_files:
            logger.info("\nThe following files are not of a supported file type, missing a corresponding .ocr.json file, or both:")
            for local_file_path in incompatible_files:
                logger.info(f"\t{local_file_path}")
            logger.info("Please ensure you run analyze_layout() to create .ocr.json files before uploading documents. \nVisit the following link for more information on supported file types and sizes. \nhttps://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/concept-custom-classifier?view=doc-intel-4.0.0#input-requirements")
        
        logger.info("Batch upload completed!")


    def print_classifier_results(self, result: Any) -> None:
        """
        Prints the results of the classifier build.

        :param result: The result object from the classifier build.
        """
        try:
            logger.info(f"Classifier ID: {result.classifier_id}")
            logger.info(
                f"API version used to build the classifier model: {result.api_version}"
            )
            logger.info(f"Classifier description: {result.description}")
            logger.info(f"Document classes used for training the model:")
            for doc_type in result.doc_types.items():
                logger.info(f"Document type: {doc_type}")
        except Exception as e:
            logger.error(f"Failed to print classifier results: {e}")
            raise


class DocumentClassifierInference:
    def __init__(self, endpoint: str, key: str, classifier_id: str):
        """
        Initialize the DocumentClassifier with the necessary configurations and clients.

        Parameters:
        endpoint (str): The endpoint for the Azure Document Intelligence service.
        key (str): The key for the Azure Document Intelligence service.
        classifier_id (str): The ID of the trained document classifier.
        """
        self.endpoint = endpoint
        self.key = key
        self.classifier_id = classifier_id
        self.client = DocumentIntelligenceClient(
            endpoint=self.endpoint, credential=AzureKeyCredential(self.key)
        )

    def classify_document(self, doc: Union[str, bytes]) -> AnalyzeResult:
        """
        Classify a document using the trained classifier.

        :param doc: Path to the document file or bytes object containing the document.
        :return: AnalyzeResult object containing classification results.
        """
        try:
            if isinstance(doc, str):
                # Determine the content type based on the file extension
                content_type, _ = mimetypes.guess_type(doc)
                if content_type is None:
                    raise ValueError(f"Unsupported file type for {doc}")
                with open(doc, "rb") as f:
                    classify_request = f.read()
            elif isinstance(doc, bytes):
                # Assume the content type is application/octet-stream for bytes input
                content_type = "application/octet-stream"
                classify_request = doc
            else:
                raise ValueError("Input must be a file path or bytes object")

            poller = self.client.begin_classify_document(
                self.classifier_id,
                classify_request=classify_request,
                content_type=content_type,
            )
            result = poller.result()
            logger.info(f"Classified document: {doc if isinstance(doc, str) else 'bytes object'}")
            return result
        except HttpResponseError as e:
            logger.error(f"Error classifying document {doc if isinstance(doc, str) else 'bytes object'}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during classification of {doc if isinstance(doc, str) else 'bytes object'}: {e}")
            raise

    def classify_documents_in_directory(
        self, directory: str, max_workers: int = 4
    ) -> None:
        """
        Classify all documents in the specified directory.

        :param directory: Path to the directory containing documents to be classified.
        :param max_workers: Number of threads to use for parallel processing.
        """
        files_to_classify = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith((".pdf",))
        ]
        total_files = len(files_to_classify)

        if not files_to_classify:
            logger.info("No documents to classify. Exiting.")
            return

        logger.info(f"Starting classification of {total_files} files...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.classify_document, file_path): file_path
                for file_path in files_to_classify
            }

            for future in as_completed(futures):
                file_path = futures[future]
                try:
                    result = future.result()
                    self.print_classification_result(result)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {e}")

        logger.info("Batch classification completed!")

    def print_classification_result(self, result: AnalyzeResult) -> None:
        """
        Print the classification results.

        :param result: AnalyzeResult object containing classification results.
        """
        logger.info("----Classified documents----")
        if result.documents:
            for doc in result.documents:
                if doc.bounding_regions:
                    logger.info(
                        f"Found document of type '{doc.doc_type or 'N/A'}' with a confidence of {doc.confidence} contained on "
                        f"the following pages: {[region.page_number for region in doc.bounding_regions]}"
                    )
