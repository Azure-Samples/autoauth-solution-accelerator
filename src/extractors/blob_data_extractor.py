import os
import tempfile
from io import BytesIO
from typing import Dict, List, Optional, Union

from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

from src.extractors.utils import get_container_and_blob_name_from_url
from utils.ml_logging import get_logger

# Initialize logger
logger = get_logger()


class AzureBlobDataExtractor:
    """
    Class for managing interactions with Azure Blob Storage. It provides functionalities
    to read and write data to blobs, especially focused on handling various file formats.

    Attributes:
        container_name (str): Name of the Azure Blob Storage container.
        service_client (BlobServiceClient): Azure Blob Service Client.
        container_client: Azure Container Client specific to the container.
    """

    def __init__(self, container_name: Optional[str] = None):
        """
        Initialize the AzureBlobManager with a container name.

        Args:
            container_name (str, optional): Name of the Azure Blob Storage container. Defaults to None.
        """
        try:
            load_dotenv()
            connect_str = os.getenv("AZURE_BLOB_CONNECTION_STRING")
            if connect_str is None:
                logger.error(
                    "AZURE_BLOB_CONNECTION_STRING not found in environment variables."
                )
                raise EnvironmentError(
                    "AZURE_BLOB_CONNECTION_STRING not found in environment variables."
                )
            self.container_name = container_name
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connect_str
            )
            if container_name:
                self.container_client = self.blob_service_client.get_container_client(
                    container_name
                )
        except Exception as e:
            logger.error(f"Error initializing AzureBlobManager: {e}")
            raise

    def change_container(self, new_container_name: str):
        """
        Changes the Azure Blob Storage container.

        Args:
            new_container_name (str): The name of the new container.
        """
        self.container_name = new_container_name
        self.container_client = self.blob_service_client.get_container_client(
            new_container_name
        )
        logger.info(f"Container changed to {new_container_name}")

    def extract_content(self, file_path: str) -> bytes:
        """
        Downloads blobs from a container.

        :param filenames: List of filenames to be downloaded from the blob.
        :return: List of BytesIO objects representing the downloaded blobs.
        """
        blob_data = None
        (
            container_name,
            file_name,
        ) = get_container_and_blob_name_from_url(file_path)
        try:
            blob_data = (
                self.blob_service_client.get_blob_client(
                    container=container_name, blob=file_name
                )
                .download_blob()
                .readall()
            )
            logger.info(f"Successfully downloaded blob file {file_name}")
        except Exception as e:
            logger.error(f"Failed to download blob file {file_name}: {e}")
        return blob_data

    def extract_metadata(self, blob_url: str) -> Dict[str, Optional[Union[str, int]]]:
        """
        Extracts metadata from a blob in Azure Blob Storage.

        :param blob_url: URL of the blob.
        :return: Dictionary with metadata.
        """
        container_name, blob_name = get_container_and_blob_name_from_url(blob_url)
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name, blob=blob_name
            )
            blob_properties = blob_client.get_blob_properties()

            # Extracting available metadata
            return {
                "url": blob_url,
                "name": blob_name,
                "size": blob_properties.size,
                "content_type": blob_properties.content_settings.content_type,
                "last_modified": blob_properties.last_modified,
                # Add other properties as needed
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata for blob {blob_name}: {e}")
            return {}

    def format_metadata(self, metadata: Dict) -> Dict:
        """
        Format and return file metadata.

        :param metadata: Dictionary of file metadata.
        :param file_name: Name of the file.
        :param users_by_role: Dictionary of users grouped by their role.
        :return: Formatted metadata as a dictionary.
        """
        formatted_metadata = {
            "source": metadata.get("url"),
            "name": metadata.get("blob_name"),
            "size": metadata.get("size"),
            "content_type": metadata.get("content_type"),
            "last_modified": (
                metadata.get("last_modified").isoformat()
                if metadata.get("last_modified")
                else None
            ),
        }
        return formatted_metadata

    def write_blob_data_to_temp_files(
        self, blob_data: List[BytesIO], filenames: List[str]
    ) -> List[str]:
        """
        Writes blobs to temporary files.

        :param blob_data: List of BytesIO objects representing the blobs.
        :param filenames: List of filenames corresponding to the blobs.
        :return: List of paths to the temporary files.
        """
        temp_dir = tempfile.mkdtemp()
        temp_files = []
        for i, byteio in enumerate(blob_data):
            try:
                file_path = os.path.join(temp_dir, filenames[i])
                with open(file_path, "wb") as file:
                    file.write(byteio.getbuffer())
                temp_files.append(file_path)
            except Exception as e:
                logger.error(
                    f"Failed to write blob data to temp file {filenames[i]}: {e}"
                )
        return temp_files

    def download_files_to_folder(self, folder_path: str, local_dir: str) -> None:
        """
        Downloads all files from a specified folder in Azure Blob Storage to a local directory.

        Args:
            folder_path (str): The path to the folder within the blob container.
            local_dir (str): The local directory to which the files will be downloaded.
        """
        try:
            # Ensure folder path ends with a '/'
            if not folder_path.endswith("/"):
                folder_path += "/"
                logger.info(f"Folder path {folder_path}")

            blob_list = self.container_client.list_blobs()
            for blob in blob_list:
                logger.info(f"{blob.name}")
                local_file_path = os.path.join(local_dir, os.path.basename(blob.name))
                blob_client = self.container_client.get_blob_client(blob.name)
                with open(local_file_path, "wb") as file:
                    downloader = blob_client.download_blob()
                    file.write(downloader.readall())

                logger.info(f"Downloaded {blob.name} to {local_file_path}")

        except Exception as e:
            logger.error(f"An error occurred while downloading files: {e}")
            raise
