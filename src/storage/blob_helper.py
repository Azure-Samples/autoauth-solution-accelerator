import os
from typing import Dict, List, Optional
from urllib.parse import urlparse

from azure.core.credentials import AzureNamedKeyCredential
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient, BlobServiceClient
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.ml_logging import get_logger

# Initialize logger
logger = get_logger()


class AzureBlobManager:
    """
    A class for managing interactions with Azure Blob Storage.

    Provides functionalities to upload and download blobs, handle various file formats,
    and manage blob metadata.
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
            self.storage_account_name = storage_account_name or os.getenv(
                "AZURE_STORAGE_ACCOUNT_NAME"
            )
            self.container_name = container_name or os.getenv(
                "AZURE_BLOB_CONTAINER_NAME"
            )
            self.account_key = account_key or os.getenv("AZURE_STORAGE_ACCOUNT_KEY")

            if not self.storage_account_name:
                raise ValueError(
                    "Storage account name must be provided either as a parameter or in the .env file."
                )
            if not self.container_name:
                raise ValueError(
                    "Container name must be provided either as a parameter or in the .env file."
                )
            credential = DefaultAzureCredential()
            storage_conn_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if "ResourceId=" not in storage_conn_string:
                if not self.account_key:
                    raise ValueError(
                        "Storage account key must be provided either as a parameter or in the .env file."
                    )
                credential = AzureNamedKeyCredential(
                    self.storage_account_name, self.account_key
                )
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{self.storage_account_name}.blob.core.windows.net",
                credential=credential,
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            self._create_container_if_not_exists()

        except Exception as e:
            logger.error(f"Error initializing AzureBlobManager: {e}")
            raise

    def _create_container_if_not_exists(self) -> None:
        """
        Creates the blob container if it does not already exist.
        """
        try:
            if self.container_client and not self.container_client.exists():
                self.container_client.create_container()
                logger.info(f"Created container '{self.container_name}'.")
            else:
                logger.info(f"Container '{self.container_name}' already exists.")
        except Exception as e:
            logger.error(
                f"Failed to create or access container '{self.container_name}': {e}"
            )
            raise

    def change_container(self, new_container_name: str) -> None:
        """
        Changes the Azure Blob Storage container.

        Args:
            new_container_name (str): The name of the new container.
        """
        try:
            self.container_name = new_container_name
            self.container_client = self.blob_service_client.get_container_client(
                new_container_name
            )
            self._create_container_if_not_exists()
            logger.info(f"Container changed to '{new_container_name}'.")
        except Exception as e:
            logger.error(f"Failed to change container to '{new_container_name}': {e}")
            raise

    def _parse_blob_url(self, blob_url: str) -> Dict[str, str]:
        """
        Parses a blob URL and extracts the storage account name, container name, and blob name.

        Args:
            blob_url (str): The full URL to the blob.

        Returns:
            Dict[str, str]: A dictionary containing 'storage_account', 'container_name', and 'blob_name'.
        """
        parsed_url = urlparse(blob_url)
        storage_account = parsed_url.netloc.split(".")[0]
        path_parts = parsed_url.path.lstrip("/").split("/")
        container_name = path_parts[0]
        blob_name = "/".join(path_parts[1:])
        return {
            "storage_account": storage_account,
            "container_name": container_name,
            "blob_name": blob_name,
        }

    def _check_file_exists_and_permissions(self, file_path: str) -> bool:
        """
        Checks if a file exists and has read permissions.

        Args:
            file_path (str): Path to the file.

        Returns:
            bool: True if the file exists and has read permissions, False otherwise.
        """
        if not os.path.isfile(file_path):
            logger.error(f"File '{file_path}' does not exist.")
            return False
        if not os.access(file_path, os.R_OK):
            logger.error(f"Permission denied: '{file_path}'")
            return False
        return True

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(2)
    )
    def upload_file(
        self,
        local_file_path: str,
        remote_blob_path: str,
        overwrite: bool = False,
        extension: Optional[str] = None,
    ) -> None:
        """
        Uploads a single file or all files with a specific extension to Azure Blob Storage.

        Args:
            local_file_path (str): Path to the local file or directory to upload.
            remote_blob_path (str): The destination path in the blob storage.
            overwrite (bool, optional): Whether to overwrite existing blobs. Defaults to False.
            extension (Optional[str], optional): File extension to filter files for upload. If provided, all files with this extension in the directory will be uploaded.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return

        if extension:
            self._upload_files_with_extension(
                local_file_path, remote_blob_path, extension, overwrite
            )
        else:
            self._upload_single_file(local_file_path, remote_blob_path, overwrite)

    def _upload_single_file(
        self, local_file_path: str, remote_blob_path: str, overwrite: bool
    ) -> None:
        """
        Uploads a single file to Azure Blob Storage.

        Args:
            local_file_path (str): Path to the local file to upload.
            remote_blob_path (str): The destination path in the blob storage.
            overwrite (bool): Whether to overwrite existing blobs.
        """
        if not self._check_file_exists_and_permissions(local_file_path):
            return

        try:
            blob_client = self.container_client.get_blob_client(remote_blob_path)
            with open(local_file_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=overwrite)
            logger.info(
                f"File '{local_file_path}' uploaded to blob '{remote_blob_path}' successfully."
            )
        except Exception as e:
            logger.error(
                f"Failed to upload file '{local_file_path}' to blob '{remote_blob_path}': {e}"
            )
            raise

    def _upload_files_with_extension(
        self,
        directory_path: str,
        remote_blob_path: str,
        extension: str,
        overwrite: bool,
    ) -> None:
        """
        Uploads all files with a specific extension from a directory to Azure Blob Storage.

        Args:
            directory_path (str): Path to the local directory containing files to upload.
            remote_blob_path (str): The destination path in the blob storage.
            extension (str): File extension to filter files for upload.
            overwrite (bool): Whether to overwrite existing blobs.
        """
        if not os.path.isdir(directory_path):
            logger.error(f"Directory '{directory_path}' does not exist.")
            return

        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.lower().endswith(extension.lower()):
                    file_path = os.path.join(root, file_name)
                    blob_path = os.path.join(
                        remote_blob_path, os.path.relpath(file_path, directory_path)
                    ).replace("\\", "/")

                    if not self._check_file_exists_and_permissions(file_path):
                        continue

                    try:
                        blob_client = self.container_client.get_blob_client(blob_path)
                        with open(file_path, "rb") as data:
                            blob_client.upload_blob(data, overwrite=overwrite)
                        logger.info(
                            f"File '{file_path}' uploaded to blob '{blob_path}' successfully."
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to upload file '{file_path}' to blob '{blob_path}': {e}"
                        )
                        raise

    def copy_blob(self, source_blob_url: str, destination_blob_path: str) -> None:
        """
        Copies a blob from a source URL to a destination within the storage account.

        Args:
            source_blob_url (str): The URL of the source blob.
            destination_blob_path (str): The destination path in the blob storage.
        """
        if not self.container_client:
            logger.error("Container client is not initialized.")
            return

        try:
            blob_client = self.container_client.get_blob_client(destination_blob_path)
            blob_client.start_copy_from_url(source_blob_url)
            logger.info(
                f"Started copying blob from '{source_blob_url}' to '{destination_blob_path}' in container '{self.container_name}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to copy blob from '{source_blob_url}' to '{destination_blob_path}': {e}"
            )

    def download_blob_to_file(
        self, remote_blob_path: str, local_file_path: str
    ) -> None:
        """
        Downloads a blob from Azure Blob Storage to a local file.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.
            local_file_path (str): The local file path where the blob will be saved.
        """
        try:
            blob_client = self._get_blob_client(remote_blob_path)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
            logger.info(
                f"Downloaded blob '{blob_client.blob_name}' to '{local_file_path}'."
            )
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
        try:
            blob_client = self._get_blob_client(remote_blob_path)
            blob_data = blob_client.download_blob().readall()
            logger.info(f"Downloaded blob '{blob_client.blob_name}' as bytes.")
            return blob_data
        except Exception as e:
            logger.error(f"Failed to download blob '{remote_blob_path}': {e}")
            return None

    def _get_blob_client(self, remote_blob_path: str) -> BlobClient:
        """
        Gets a BlobClient for the specified blob path or URL.

        Args:
            remote_blob_path (str): The path to the blob in the container or the full blob URL.

        Returns:
            BlobClient: The BlobClient for the specified blob.
        """
        if remote_blob_path.startswith("http"):
            return BlobClient.from_blob_url(
                blob_url=remote_blob_path,
                credential=self.blob_service_client.credential,
            )
        else:
            return self.container_client.get_blob_client(remote_blob_path)

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
            logger.info(
                f"Listed {len(blob_names)} blobs with prefix '{prefix}' in container '{self.container_name}'."
            )
            return blob_names
        except Exception as e:
            logger.error(
                f"Failed to list blobs with prefix '{prefix}' in container '{self.container_name}': {e}"
            )
            return []
