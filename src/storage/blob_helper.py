import os
import fnmatch
from typing import Optional, Callable
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.identity import DefaultAzureCredential
from utils.ml_logging import get_logger

class AzureBlobUploader:
    """
    A class for uploading files to Azure Blob Storage with optional filtering
    and the ability to specify a remote folder path.
    """

    def __init__(
        self,
        connection_string: str,
        container_name: str,
        use_user_identity: bool = True
    ):
        """
        Initializes the AzureBlobUploader with Azure Blob Storage connection details.

        Args:
            connection_string (str): Azure Blob Storage connection string.
            container_name (str): Name of the blob container.
            use_user_identity (bool, optional): Use user identity for authentication. Defaults to True.
        """
        self.connection_string = connection_string
        self.container_name = container_name
        self.use_user_identity = use_user_identity

        # Set up logging
        self.logger = get_logger()

        # Initialize the BlobServiceClient
        credential = DefaultAzureCredential() if self.use_user_identity else None
        self.blob_service_client = BlobServiceClient.from_connection_string(
            conn_str=self.connection_string,
            credential=credential,
        )
        self.container_client = self.blob_service_client.get_container_client(self.container_name)
        self._create_container_if_not_exists()

    def _create_container_if_not_exists(self) -> None:
        """
        Creates the blob container if it does not already exist.
        """
        if not self.container_client.exists():
            self.container_client.create_container()
            self.logger.info(f"Created container '{self.container_name}'.")
        else:
            self.logger.info(f"Container '{self.container_name}' already exists.")

    def upload_files(
        self,
        local_path: str,
        remote_path: str = "",
        file_filter: Optional[Callable[[str], bool]] = None,
        overwrite: bool = False
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
                    self.logger.info(f"Uploaded '{blob_name}' to blob storage.")
                else:
                    self.logger.info(f"Blob '{blob_name}' already exists. Skipping upload.")

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
