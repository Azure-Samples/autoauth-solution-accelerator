import os
import tempfile
import shutil
from typing import List, Optional
from urllib.parse import urlparse

import fitz  # PyMuPDF
from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger

# Initialize logger
logger = get_logger()

class OCRHelper:
    """
    Class for OCR functionalities, particularly extracting images from PDF files.
    """

    def __init__(
        self,
        storage_account_name: Optional[str] = None,
        container_name: Optional[str] = None,
        account_key: Optional[str] = None,
    ):
        """
        Initialize the OCRHelper with an optional AzureBlobManager.

        Args:
            storage_account_name (Optional[str]): Name of the Azure Storage account.
            container_name (Optional[str]): Name of the Azure Blob Storage container.
            account_key (Optional[str]): Storage account key for authentication.
        """
        try:
            if storage_account_name and container_name and account_key:
                self.blob_manager = AzureBlobManager(
                    storage_account_name=storage_account_name,
                    container_name=container_name,
                    account_key=account_key,
                )
                logger.info("AzureBlobManager initialized successfully.")
            else:
                self.blob_manager = None
                logger.warning("AzureBlobManager not initialized. Only local files will be processed.")
        except Exception as e:
            logger.error(f"Error initializing AzureBlobManager: {e}")
            self.blob_manager = None

    def extract_images_from_pdf(self, input_path: str, output_path: Optional[str] = None, dpi: int = 144) -> List[str]:
        """
        Extracts pages from a PDF file or a folder of PDF files and saves them as images.

        Args:
            input_path (str): Path or URL to the PDF file or folder of PDF files.
            output_path (Optional[str]): Path to the folder where the images will be saved.
                                         If None, a temporary directory is used and cleaned up after extraction.
            dpi (int, optional): DPI for the output images. Defaults to 144.

        Returns:
            List[str]: List of paths to the extracted images.
        """
        image_paths = []
        temp_dir = None  # To track if a temporary directory is used

        try:
            is_url = self._is_url(input_path)

            if is_url:
                logger.info(f"Input path is a URL: {input_path}")
                if self.blob_manager:
                    temp_dir = tempfile.mkdtemp()
                    blob_name = self._get_blob_name_from_url(input_path)
                    local_file_path = os.path.join(temp_dir, os.path.basename(blob_name))
                    
                    logger.info(f"Downloading blob '{blob_name}' to temporary directory '{temp_dir}'.")
                    self.blob_manager.download_blob_to_file(
                        remote_blob_path=blob_name,
                        local_file_path=local_file_path
                    )
                    
                    extracted_images = self._process_pdf_path(local_file_path, output_path or temp_dir, dpi)
                    image_paths.extend(extracted_images)
                else:
                    logger.error("BlobManager is not initialized. Cannot handle URL input.")
                    raise Exception("BlobManager is not initialized. Cannot handle URL input.")
            else:
                logger.info(f"Input path is a local file or directory: {input_path}")
                extracted_images = self._process_pdf_path(input_path, output_path, dpi)
                image_paths.extend(extracted_images)

            return image_paths

        except Exception as e:
            logger.error(f"Failed to extract images from PDF: {e}")
            raise

        finally:
            # Clean up temporary directory if it was used and no output_path was provided
            if temp_dir and not output_path:
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to clean up temporary directory '{temp_dir}': {cleanup_error}")

    def _process_pdf_path(self, input_path: str, output_path: str, dpi: int) -> List[str]:
        """
        Processes a PDF file or all PDF files in a directory.

        Args:
            input_path (str): Path to the PDF file or directory containing PDF files.
            output_path (str): Path to save the extracted images.
            dpi (int): DPI for the output images.

        Returns:
            List[str]: List of paths to the extracted images.
        """
        image_paths = []
        try:
            if os.path.isdir(input_path):
                image_paths.extend(self._process_pdf_directory(input_path, output_path, dpi))
            elif os.path.isfile(input_path) and input_path.lower().endswith(".pdf"):
                image_paths.extend(self._process_single_pdf(input_path, output_path, dpi))
            else:
                logger.error("The input path is neither a valid PDF file nor a directory.")
                raise ValueError("The input path is neither a valid PDF file nor a directory.")
        except Exception as e:
            logger.error(f"Failed to process PDF path: {e}")
            raise
        return image_paths

    def _process_pdf_directory(self, directory_path: str, output_path: str, dpi: int) -> List[str]:
        """
        Processes all PDF files in a directory and its subdirectories, saving each page as an image.

        Args:
            directory_path (str): Directory containing PDF files.
            output_path (str): Directory where the images will be saved.
            dpi (int): DPI for the output images.

        Returns:
            List[str]: List of paths to the extracted images.
        """
        image_paths = []
        try:
            all_files = self._find_all_pdfs(directory_path)
            logger.info(f"Found {len(all_files)} PDF files in '{directory_path}' and its subdirectories.")
            for file_path in all_files:
                logger.info(f"Processing file: {file_path}")
                extracted_images = self._process_single_pdf(file_path, output_path, dpi)
                image_paths.extend(extracted_images)
        except Exception as e:
            logger.error(f"Failed to process PDF directory: {e}")
            raise
        return image_paths

    def _find_all_pdfs(self, directory_path: str) -> List[str]:
        """
        Recursively finds all PDF files in a directory and its subdirectories.

        Args:
            directory_path (str): Directory to search for PDF files.

        Returns:
            List[str]: List of paths to PDF files.
        """
        try:
            pdf_files = []
            for root, _, files in os.walk(directory_path):
                for file in files:
                    if file.lower().endswith(".pdf"):
                        pdf_files.append(os.path.join(root, file))
            logger.debug(f"PDF files found: {pdf_files}")
            return pdf_files
        except Exception as e:
            logger.error(f"Failed to find PDF files in directory '{directory_path}': {e}")
            raise

    def _process_single_pdf(self, file_path: str, output_path: str, dpi: int) -> List[str]:
        """
        Processes a single PDF file and saves each page as an image.

        Args:
            file_path (str): Path to the PDF file.
            output_path (str): Directory where the images will be saved.
            dpi (int): DPI for the output images.

        Returns:
            List[str]: List of paths to the extracted images.
        """
        image_paths = []
        try:
            zoom_factor = dpi / 72.0  # 72 DPI is the default resolution
            mat = fitz.Matrix(zoom_factor, zoom_factor)

            logger.info(f"Opening file: {file_path}")
            doc = fitz.open(file_path)
            base_filename = os.path.splitext(os.path.basename(file_path))[0]

            for page_number, page in enumerate(doc):
                logger.info(f"Processing page {page_number + 1} of '{file_path}'")
                pix = page.get_pixmap(matrix=mat)
                output_filename = f"{base_filename}-page-{page_number + 1}.png"
                full_output_path = os.path.join(output_path, output_filename)

                os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

                pix.save(full_output_path)
                logger.info(f"Saved image: {full_output_path}")
                image_paths.append(full_output_path)

        except Exception as e:
            logger.error(f"Failed to process single PDF '{file_path}': {e}")
            raise
        return image_paths

    def _is_url(self, path: str) -> bool:
        """
        Determines if a given path is a URL.

        Args:
            path (str): The path to check.

        Returns:
            bool: True if the path is a URL, False otherwise.
        """
        parsed = urlparse(path)
        return parsed.scheme in ["http", "https"]

    def _get_blob_name_from_url(self, url: str) -> str:
        """
        Extracts the blob name from a given Azure Blob URL.

        Args:
            url (str): The full URL to the blob.

        Returns:
            str: The blob name.
        """
        parsed_url = urlparse(url)
        path_parts = parsed_url.path.lstrip('/').split('/', 1)
        if len(path_parts) == 2:
            container, blob_name = path_parts
            return blob_name
        else:
            logger.error(f"Invalid blob URL format: {url}")
            raise ValueError(f"Invalid blob URL format: {url}")
