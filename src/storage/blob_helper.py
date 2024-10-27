import os
import fnmatch
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from urllib.parse import urlparse

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.credentials import AzureNamedKeyCredential
from dotenv import load_dotenv

from utils.ml_logging import get_logger

# Initialize logger
logger = get_logger()


class AzureBlobManager:
    """
    A class for managing interactions with Azure Blob Storage.

    Provides functionalities to upload and download blobs, handle various file formats,
    and manage blob metadata.

    Attributes:
        storage_account_name (str): Name of the Azure Storage account.
        container_name (str): Name of the blob container.
        account_key (str): Storage account key for authentication.
        blob_service_client (BlobServiceClient): Azure Blob Service Client.
        container_client (ContainerClient): Azure Container Client specific to the container.
    """

    def __init__(
        self,
        storage_account_name: Optional[str] = None,
        container_name: Optional[str] = None,
        account_key: Optional[str] = None,
    ):
        """
        Initialize the AzureBlobManager.

        Args:
            storage_account_name (Optional[str]): Name of the Azure Storage account.
            container_name (Optional[str]): Name of the blob container.
            account_key (Optional[str]): Storage account key for authentication.
        """
        try:
            load_dotenv()
            self.storage_account_name = storage_account_name or os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
            self.container_name = container_name or os.getenv("AZURE_BLOB_CONTAINER_NAME")
            self.account_key = account_key or os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

            if not self.storage_account_name:
                raise ValueError("Storage account name must be provided either as a parameter or in the .env file.")
            if not self.container_name:
                raise ValueError("Container name must be provided either as a parameter or in the .env file.")
            if not self.account_key:
                raise ValueError("Storage account key must be provided either as a parameter or in the .env file.")

            # Initialize the BlobServiceClient with the account key
            credential = AzureNamedKeyCredential(self.storage_account_name, self.account_key)
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
                credential=credential,
            )
            self.container_client = self.blob_service_client.get_container_client(self.container_name)
            self._create_container_if_not_exists()

        except Exception as e:
            logger.error(f"Error initializing AzureBlobManager: {e}")
            raise

    def _create_container_if_not_exists(self) -> None:
        """
        Creates the blob container if it does not already exist.
        """
        if self.container_client and not self.container_client.exists():
            self.container_client.create_container()
            logger.info(f"Created container '{self.container_name}'.")
        else:
            logger.info(f"Container '{self.container_name}' already exists or not specified.")

    def change_container(self, new_container_name: str) -> None:
        """
        Changes the Azure Blob Storage container.

        Args:
            new_container_name (str): The name of the new container.
        """
        self.container_name = new_container_name
        self.container_client = self.blob_service_client.get_container_client(new_container_name)
        self._create_container_if_not_exists()
        logger.info(f"Container changed to {new_container_name}")

    def _parse_blob_url(self, blob_url: str) -> Dict[str, str]:
        """
        Parses a blob URL and extracts the storage account name, container name, and blob name.

        Args:
            blob_url (str): The full URL to the blob.

        Returns:
            Dict[str, str]: A dictionary containing 'storage_account', 'container_name', and 'blob_name'.
        """
        parsed_url = urlparse(blob_url)
        storage_account = parsed_url.netloc.split('.')[0]
        path_parts = parsed_url.path.lstrip('/').split('/')
        container_name = path_parts[0]
        blob_name = '/'.join(path_parts[1:])
        return {
            'storage_account': storage_account,
            'container_name': container_name,
            'blob_name': blob_name
        }

    def upload_files(
        self,
        local_path: str,
        remote_path: str = "",
        file_filter: Optional[Callable[[str], bool]] = None,
        overwrite: bool = False,
    ) -> None:
        """
        Uploads files from a local directory to Azure Blob Storage, with optional filtering
        and specifying a remote folder path in the blob storage.

        Args:
            local_path (str): Local directory path to upload files from.
            remote_path (str, optional): Remote directory path in the blob container where files will be uploaded.
                Defaults to "" (root of the container).
            file_filter (Optional[Callable[[str], bool]], optional): Function to filter files.
                Should return True for files to upload. Defaults to None.
            overwrite (bool, optional): Whether to overwrite existing blobs. Defaults to False.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return

        for root, _, files in os.walk(local_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)

                # Apply the file filter if provided
                if file_filter and not file_filter(file_path):
                    continue

                # Generate blob name while preserving directory structure
                relative_path = os.path.relpath(file_path, local_path).replace("\\", "/")
                blob_name = os.path.join(remote_path, relative_path).replace("\\", "/")

                # Upload the file, optionally overwriting existing blobs
                blob_client = self.container_client.get_blob_client(blob_name)
                if overwrite or not blob_client.exists():
                    with open(file_path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=overwrite)
                    logger.info(f"Uploaded '{blob_name}' to blob storage.")
                else:
                    logger.info(f"Blob '{blob_name}' already exists. Skipping upload.")

    def download_blob_to_file(self, remote_blob_path: str, local_file_path: str) -> None:
        """
        Downloads a blob from Azure Blob Storage to a local file.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.
            local_file_path (str): The local file path where the blob will be saved.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return

        try:
            # Check if remote_blob_path is a URL
            if remote_blob_path.startswith("http"):
                blob_info = self._parse_blob_url(remote_blob_path)
                if blob_info['storage_account'] != self.storage_account_name:
                    raise ValueError("Blob URL points to a different storage account.")
                if blob_info['container_name'] != self.container_name:
                    self.change_container(blob_info['container_name'])
                blob_name = blob_info['blob_name']
            else:
                blob_name = remote_blob_path

            blob_client = self.container_client.get_blob_client(blob_name)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            logger.info(f"Downloaded blob '{blob_name}' to '{local_file_path}'.")
        except Exception as e:
            logger.error(f"Failed to download blob '{remote_blob_path}': {e}")

    def download_blob_to_bytes(self, remote_blob_path: str) -> Optional[bytes]:
        """
        Downloads a blob from Azure Blob Storage and returns its content as bytes.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.

        Returns:
            Optional[bytes]: The content of the blob as bytes, or None if an error occurred.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return None

        try:
            # Check if remote_blob_path is a URL
            if remote_blob_path.startswith("http"):
                blob_info = self._parse_blob_url(remote_blob_path)
                if blob_info['storage_account'] != self.storage_account_name:
                    raise ValueError("Blob URL points to a different storage account.")
                if blob_info['container_name'] != self.container_name:
                    self.change_container(blob_info['container_name'])
                blob_name = blob_info['blob_name']
            else:
                blob_name = remote_blob_path

            blob_client = self.container_client.get_blob_client(blob_name)
            blob_data = blob_client.download_blob().readall()
            logger.info(f"Downloaded blob '{blob_name}' as bytes.")
            return blob_data
        except Exception as e:
            logger.error(f"Failed to download blob '{remote_blob_path}': {e}")
            return None

    def download_blobs_to_folder(self, remote_folder_path: str, local_folder_path: str) -> None:
        """
        Downloads all blobs from a specified folder in Azure Blob Storage to a local directory.

        Args:
            remote_folder_path (str): The path to the folder within the blob container or the full URL.
            local_folder_path (str): The local directory to which the files will be downloaded.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return

        try:
            # Check if remote_folder_path is a URL
            if remote_folder_path.startswith("http"):
                blob_info = self._parse_blob_url(remote_folder_path)
                if blob_info['storage_account'] != self.storage_account_name:
                    raise ValueError("Blob URL points to a different storage account.")
                if blob_info['container_name'] != self.container_name:
                    self.change_container(blob_info['container_name'])
                remote_folder_path = blob_info['blob_name']

            # Ensure remote folder path ends with '/'
            if not remote_folder_path.endswith("/"):
                remote_folder_path += "/"

            blobs_list = self.container_client.list_blobs(name_starts_with=remote_folder_path)
            for blob in blobs_list:
                relative_path = os.path.relpath(blob.name, remote_folder_path).replace("/", os.sep)
                local_file_path = os.path.join(local_folder_path, relative_path)
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                self.download_blob_to_file(blob.name, local_file_path)
                logger.info(f"Downloaded {blob.name} to {local_file_path}")

        except Exception as e:
            logger.error(f"An error occurred while downloading files: {e}")

    def get_blob_metadata(self, remote_blob_path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves metadata of a blob in Azure Blob Storage.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.

        Returns:
            Optional[Dict[str, Any]]: Dictionary containing metadata of the blob, or None if an error occurred.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return None

        try:
            # Check if remote_blob_path is a URL
            if remote_blob_path.startswith("http"):
                blob_info = self._parse_blob_url(remote_blob_path)
                if blob_info['storage_account'] != self.storage_account_name:
                    raise ValueError("Blob URL points to a different storage account.")
                if blob_info['container_name'] != self.container_name:
                    self.change_container(blob_info['container_name'])
                blob_name = blob_info['blob_name']
            else:
                blob_name = remote_blob_path

            blob_client = self.container_client.get_blob_client(blob_name)
            blob_properties = blob_client.get_blob_properties()

            metadata = {
                "name": blob_client.blob_name,
                "size": blob_properties.size,
                "content_type": blob_properties.content_settings.content_type,
                "last_modified": blob_properties.last_modified.isoformat(),
                "etag": blob_properties.etag,
                "metadata": blob_properties.metadata,
            }
            logger.info(f"Retrieved metadata for blob '{blob_name}'.")
            return metadata
        except Exception as e:
            logger.error(f"Failed to get metadata for blob '{remote_blob_path}': {e}")
            return None

    def list_blobs(self, prefix: str = "") -> List[str]:
        """
        Lists all blobs in the container, optionally filtered by a prefix.

        Args:
            prefix (str, optional): Filter blobs whose names begin with this prefix. Defaults to "".

        Returns:
            List[str]: List of blob names.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return []

        try:
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            blob_names = [blob.name for blob in blobs]
            logger.info(f"Listed {len(blob_names)} blobs with prefix '{prefix}'.")
            return blob_names
        except Exception as e:
            logger.error(f"Failed to list blobs with prefix '{prefix}': {e}")
            return []

    @staticmethod
    def filter_by_extension(extension: str) -> Callable[[str], bool]:
        """
        Creates a filter function to filter files by extension.

        Args:
            extension (str): File extension to filter by (e.g., '.pdf').

        Returns:
            Callable[[str], bool]: Function that returns True if a file has the specified extension.
        """
        def filter_func(file_path: str) -> bool:
            return file_path.lower().endswith(extension.lower())
        return filter_func

    @staticmethod
    def filter_by_name(name_pattern: str) -> Callable[[str], bool]:
        """
        Creates a filter function to filter files by name pattern.

        Args:
            name_pattern (str): File name pattern to filter by (supports wildcards, e.g., 'report_*.txt').

        Returns:
            Callable[[str], bool]: Function that returns True if a file matches the name pattern.
        """
        def filter_func(file_path: str) -> bool:
            return fnmatch.fnmatch(os.path.basename(file_path), name_pattern)
        return filter_func

    def get_blob_client(self, remote_blob_path: str) -> BlobClient:
        """
        Retrieves a BlobClient for a specific blob.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.

        Returns:
            BlobClient: The BlobClient object for the specified blob.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            raise ValueError("Container client is not initialized.")

        # Check if remote_blob_path is a URL
        if remote_blob_path.startswith("http"):
            blob_info = self._parse_blob_url(remote_blob_path)
            if blob_info['storage_account'] != self.storage_account_name:
                raise ValueError("Blob URL points to a different storage account.")
            if blob_info['container_name'] != self.container_name:
                self.change_container(blob_info['container_name'])
            blob_name = blob_info['blob_name']
        else:
            blob_name = remote_blob_path

        return self.container_client.get_blob_client(blob_name)
