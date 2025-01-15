import io
import os
import tempfile
from typing import List, Optional
from urllib.parse import urlparse

import fitz
from PyPDF2 import PdfFileReader

from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger

logger = get_logger()
logger = get_logger()


class PDFHelper:
    """This class facilitates the processing of PDF files.
    It supports loading configuration from environment variables and provides methods for PDF text extraction.
    """

    def __init__(self):
        """
        Initialize the PDFHelper class.
        """
        logger.info("PDFHelper initialized.")

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extracts text from a PDF file provided as a bytes object.
        :param pdf_bytes: Bytes object containing the PDF file data.
        :return: Extracted text from the PDF as a string, or None if extraction fails.
        """
        try:
            with io.BytesIO(pdf_bytes) as pdf_stream:
                return self._extract_text_from_pdf(pdf_stream)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during PDF text extraction: {e}"
            )
            return None

    def extract_text_from_pdf_file(self, file_path: str) -> str:
        """
        Extracts text from a PDF file located at the given file path.
        :param file_path: Path to the PDF file.
        :return: Extracted text from the PDF as a string, or None if extraction fails.
        """
        try:
            with open(file_path, "rb") as file:
                return self._extract_text_from_pdf(file)
        except Exception as e:
            logger.error(f"An unexpected error occurred when opening the PDF file: {e}")
            return None

    def _extract_text_from_pdf(self, file_stream) -> str:
        """
        Helper method to extract text from a PDF file stream.
        :param file_stream: File stream of the PDF file.
        :return: Extracted text from the PDF as a string, or None if extraction fails.
        """
        try:
            pdf_reader = PdfFileReader(file_stream)
            text = []
            for page_num in range(pdf_reader.getNumPages()):
                page = pdf_reader.getPage(page_num)
                text.append(page.extractText())

            extracted_text = "\n".join(text)
            logger.info("Text extraction from PDF was successful.")
            return extracted_text
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during PDF text extraction: {e}"
            )
            return None

    def extract_metadata_from_pdf_bytes(self, pdf_bytes: bytes) -> dict:
        """
        Extracts metadata from a PDF file provided as a bytes object.

        :param pdf_bytes: Bytes object containing the PDF file data.
        :return: A dictionary containing the extracted metadata, or None if extraction fails.
        """
        try:
            with io.BytesIO(pdf_bytes) as pdf_stream:
                pdf = PdfFileReader(pdf_stream)
                information = pdf.getDocumentInfo()
                number_of_pages = pdf.getNumPages()

                metadata = {
                    "Author": information.author,
                    "Creator": information.creator,
                    "Producer": information.producer,
                    "Subject": information.subject,
                    "Title": information.title,
                    "Number of pages": number_of_pages,
                }

                logger.info("Metadata extraction from PDF bytes was successful.")
                return metadata
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during PDF metadata extraction: {e}"
            )
            return None


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
        if storage_account_name and container_name and account_key:
            self.blob_manager = AzureBlobManager(
                storage_account_name=storage_account_name,
                container_name=container_name,
                account_key=account_key,
            )
        else:
            self.blob_manager = None

    def extract_images_from_pdf(self, input_path: str, output_path: str) -> str:
        """
        Extracts pages from a PDF file or a folder of PDF files and saves them as images.

        Args:
            input_path (str): Path or URL to the PDF file or folder of PDF files.
            output_path (str): Path to the folder where the images will be saved.

        Returns:
            str: Path to the directory containing the extracted images.
        """
        is_url = urlparse(input_path).scheme in ["http", "https"]

        if is_url:
            logger.info(f"Input path is a URL: {input_path}")
            if self.blob_manager:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Download the blob to the temporary directory
                    blob_name = urlparse(input_path).path.lstrip("/")
                    local_file_path = os.path.join(
                        temp_dir, os.path.basename(blob_name)
                    )
                    self.blob_manager.download_blob_to_file(
                        remote_blob_path=blob_name, local_file_path=local_file_path
                    )
                    # Process the downloaded file
                    self._process_pdf_path(local_file_path, output_path)
            else:
                logger.error("BlobManager is not initialized. Cannot handle URL input.")
                raise Exception(
                    "BlobManager is not initialized. Cannot handle URL input."
                )
        else:
            logger.info(f"Input path is a local file or directory: {input_path}")
            self._process_pdf_path(input_path, output_path)

        return output_path

    def _process_pdf_path(self, input_path: str, output_path: str) -> None:
        """
        Processes a PDF file or all PDF files in a directory.

        Args:
            input_path (str): Path to the PDF file or directory containing PDF files.
            output_path (str): Path to save the extracted images.
        """
        if os.path.isdir(input_path):
            self._process_pdf_directory(input_path, output_path)
        elif os.path.isfile(input_path) and input_path.lower().endswith(".pdf"):
            self._process_single_pdf(input_path, output_path)
        else:
            logger.error("The input path is neither a valid PDF file nor a directory.")
            raise ValueError(
                "The input path is neither a valid PDF file nor a directory."
            )

    def _process_pdf_directory(self, directory_path: str, output_path: str) -> None:
        """
        Processes all PDF files in a directory and its subdirectories, saving each page as an image.

        Args:
            directory_path (str): Directory containing PDF files.
            output_path (str): Directory where the images will be saved.
        """
        all_files = self._find_all_pdfs(directory_path)
        logger.info(
            f"Found {len(all_files)} PDF files in {directory_path} and its subdirectories"
        )
        for file_path in all_files:
            logger.info(f"Processing file: {file_path}")
            self._process_single_pdf(file_path, output_path)

    def _find_all_pdfs(self, directory_path: str) -> List[str]:
        """
        Recursively finds all PDF files in a directory and its subdirectories.

        Args:
            directory_path (str): Directory to search for PDF files.

        Returns:
            List[str]: List of paths to PDF files.
        """
        pdf_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files

    def _process_single_pdf(self, file_path: str, output_path: str) -> None:
        """
        Processes a single PDF file and saves each page as an image.

        Args:
            file_path (str): Path to the PDF file.
            output_path (str): Directory where the images will be saved.
        """
        zoom_x = 2.0  # horizontal zoom
        zoom_y = 2.0  # vertical zoom
        mat = fitz.Matrix(zoom_x, zoom_y)  # zoom factor 2 in each dimension

        logger.info(f"Opening file: {file_path}")
        doc = fitz.open(file_path)
        base_filename = os.path.splitext(os.path.basename(file_path))[0]

        for page_number, page in enumerate(doc):
            logger.info(f"Processing page {page_number + 1} of {file_path}")
            pix = page.get_pixmap(matrix=mat)
            output_filename = f"{base_filename}-page-{page_number + 1}.png"
            full_output_path = os.path.join(output_path, output_filename)

            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

            pix.save(full_output_path)
            logger.info(f"Saved image: {full_output_path}")
