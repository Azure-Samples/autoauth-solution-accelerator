import os
from functools import lru_cache
from typing import Any, Dict, Iterator, List, Optional, Union

from azure.ai.documentintelligence import DocumentIntelligenceClient, models

# from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, Document
from azure.core.credentials import AzureKeyCredential
from azure.core.polling import LROPoller
from dotenv import load_dotenv
from langchain_core.documents import Document as LangchainDocument

from src.extractors.blob_data_extractor import AzureBlobDataExtractor
from utils.ml_logging import get_logger

# Initialize logging
logger = get_logger()


class AzureDocumentIntelligenceManager:
    """
    A class to interact with Azure's Document Analysis Client.
    """

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_key: Optional[str] = None,
        container_name: Optional[str] = None,
    ):
        """
        Initialize the class with configurations for Azure's Document Analysis Client.

        :param azure_endpoint: Endpoint URL for Azure's Document Analysis Client.
        :param azure_key: API key for Azure's Document Analysis Client.
        :param container_client: Azure Container Client specific to the container.
        """
        self.azure_endpoint = azure_endpoint
        self.azure_key = azure_key

        if not self.azure_endpoint or not self.azure_key:
            self.load_environment_variables_from_env_file()

        if not self.azure_endpoint or not self.azure_key:
            raise ValueError(
                "Azure endpoint and key must be provided either as parameters or in a .env file."
            )

        self.blob_manager = AzureBlobDataExtractor(container_name=container_name)

        self.document_analysis_client = DocumentIntelligenceClient(
            endpoint=self.azure_endpoint,
            credential=AzureKeyCredential(self.azure_key),
            headers={"x-ms-useragent": "langchain-parser/1.0.0"},
            polling_interval=30,
        )

    @lru_cache(maxsize=1)
    def load_environment_variables_from_env_file(self):
        """
        Loads required environment variables for the application from a .env file.

        This method should be called explicitly if environment variables are to be loaded from a .env file.
        """
        load_dotenv()

        self.azure_endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        self.azure_key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Check for any missing required environment variables
        required_vars = {
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT": self.azure_endpoint,
            "AZURE_DOCUMENT_INTELLIGENCE_KEY": self.azure_key,
        }

        missing_vars = [var for var, value in required_vars.items() if not value]

        if missing_vars:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

    def analyze_document(
        self,
        document_input: Union[str, bytes],
        model_type: str = "prebuilt-layout",
        pages: Optional[str] = None,
        locale: Optional[str] = None,
        string_index_type: Optional[Union[str, models.StringIndexType]] = None,
        features: Optional[List[str]] = None,
        query_fields: Optional[List[str]] = None,
        output_format: Optional[Union[str, models.ContentFormat]] = None,
        content_type: str = "application/json",
        **kwargs: Any,
    ) -> LROPoller:
        """
        Analyzes a document using Azure's Document Analysis Client with pre-trained models.

        :param document_input: URL or file path of the document to analyze.
        :param model_type: Type of pre-trained model to use for analysis. Defaults to 'prebuilt-layout'.
            Options include:
            - 'prebuilt-document': Generic document understanding.
            - 'prebuilt-layout': Extracts text, tables, selection marks, and structure elements.
            - 'prebuilt-read': Extracts print and handwritten text.
            - 'prebuilt-tax': Processes US tax documents.
            - 'prebuilt-invoice': Automates processing of invoices.
            - 'prebuilt-receipt': Scans sales receipts for key data.
            - 'prebuilt-id': Processes identity documents.
            - 'prebuilt-businesscard': Extracts information from business cards.
            - 'prebuilt-contract': Analyzes contractual agreements.
            - 'prebuilt-healthinsurancecard': Processes health insurance cards.
            Additional custom and composed models are also available. See the documentation for more details:
            `https://docs.microsoft.com/en-us/azure/cognitive-services/form-recognizer/document-analysis-overview`
        :param pages: List of 1-based page numbers to analyze.  Ex. "1-3,5,7-9".
        :param locale: Locale hint for text recognition and document analysis.
        :param string_index_type: Method used to compute string offset and length. The options are:
            - "TEXT_ELEMENTS": User-perceived display character, or grapheme cluster, as defined by Unicode 8.0.0.
            - "UNICODE_CODE_POINT": Character unit represented by a single unicode code point. Used by Python 3.
            - "UTF16_CODE_UNIT": Character unit represented by a 16-bit Unicode code unit. Used by JavaScript, Java, and .NET.
        :param features: List of optional analysis features. The options are:
            - "BARCODES": Detects barcodes in the document.
            - "FORMULAS": Detects and analyzes formulas in the document.
            - "KEY_VALUE_PAIRS": Detects and analyzes key-value pairs in the document.
            - "LANGUAGES": Detects and analyzes languages in the document.
            - "OCR_HIGH_RESOLUTION": Performs high-resolution optical character recognition (OCR) on the document.
            - "QUERY_FIELDS": Extracts specific fields from the document based on a query.
            - "STYLE_FONT": Detects and analyzes font styles in the document.
        :param query_fields: List of additional fields to extract.
        :param output_content_format: Format of the analyze result top-level content.
        :param content_type: Body Parameter content-type. Content type parameter for JSON body.
        :param kwargs: Additional keyword arguments to pass to the analysis method.
        :return: An instance of LROPoller that returns AnalyzeResult.
        """
        # Convert feature strings into DocumentAnalysisFeature objects
        if features is not None:
            features = [
                getattr(models.DocumentAnalysisFeature, feature) for feature in features
            ]

        # Check if the document_input is a URL
        if isinstance(document_input, bytes):
            poller = self.document_analysis_client.begin_analyze_document(
                model_id=model_type,
                analyze_request=AnalyzeDocumentRequest(bytes_source=document_input),
                pages=pages,
                locale=locale,
                string_index_type=string_index_type,
                features=features,
                query_fields=query_fields,
                output_content_format=output_format if output_format else "text",
                content_type=content_type,
                **kwargs,
            )
        elif document_input.startswith(("http://", "https://")):
            # If it's an HTTP URL, raise an error
            if document_input.startswith("http://"):
                raise ValueError("HTTP URLs are not supported. Please use HTTPS.")
            # If it's an HTTPS URL but contains "blob.core.windows.net", process it as a blob
            elif "blob.core.windows.net" in document_input:
                logger.info("Blob URL detected. Extracting content.")
                content_bytes = self.blob_manager.extract_content(document_input)
                poller = self.document_analysis_client.begin_analyze_document(
                    model_id=model_type,
                    analyze_request=AnalyzeDocumentRequest(base64_source=content_bytes),
                    pages=pages,
                    locale=locale,
                    string_index_type=string_index_type,
                    features=features,
                    query_fields=query_fields,
                    output_content_format=output_format if output_format else "text",
                    content_type=content_type,
                    **kwargs,
                )
            else:
                poller = self.document_analysis_client.begin_analyze_document(
                    model_id=model_type,
                    analyze_request=AnalyzeDocumentRequest(url_source=document_input),
                    pages=pages,
                    locale=locale,
                    string_index_type=string_index_type,
                    features=features,
                    query_fields=query_fields,
                    output_content_format=output_format if output_format else "text",
                    content_type=content_type,
                    **kwargs,
                )
        else:
            with open(document_input, "rb") as f:
                file_content = f.read()
                poller = self.document_analysis_client.begin_analyze_document(
                    model_id=model_type,
                    analyze_request=AnalyzeDocumentRequest(bytes_source=file_content),
                    pages=pages,
                    locale=locale,
                    string_index_type=string_index_type,
                    features=features,
                    query_fields=query_fields,
                    output_content_format=output_format if output_format else "text",
                    content_type=content_type,
                    **kwargs,
                )
        return poller.result()

    def process_invoice(self, invoice: Document) -> Dict:
        """
        Processes a single invoice and returns a dictionary with the data.

        :param invoice: The invoice to process.
        :return: A dictionary with the processed data.
        """
        invoice_data = {}
        fields = [
            "VendorName",
            "VendorAddress",
            "VendorAddressRecipient",
            "CustomerName",
            "CustomerId",
            "CustomerAddress",
            "CustomerAddressRecipient",
            "InvoiceId",
            "InvoiceDate",
            "InvoiceTotal",
            "DueDate",
            "PurchaseOrder",
            "BillingAddress",
            "BillingAddressRecipient",
            "ShippingAddress",
            "ShippingAddressRecipient",
            "SubTotal",
            "TotalTax",
            "PreviousUnpaidBalance",
            "AmountDue",
            "ServiceStartDate",
            "ServiceEndDate",
            "ServiceAddress",
            "ServiceAddressRecipient",
            "RemittanceAddress",
            "RemittanceAddressRecipient",
        ]
        for field in fields:
            field_data = invoice.fields.get(
                field, {"content": None, "confidence": None}
            )
            invoice_data[field] = {
                "content": field_data.get("content"),
                "confidence": field_data.get("confidence"),
            }
        items = []
        for idx, item in enumerate(
            invoice.fields.get("Items", {"valueArray": []}).get("valueArray")
        ):
            item_data = {}
            item_fields = [
                "Description",
                "Quantity",
                "Unit",
                "UnitPrice",
                "ProductCode",
                "Date",
                "Tax",
                "Amount",
            ]
            for item_field in item_fields:
                item_field_data = item.get("valueObject").get(
                    item_field, {"content": None, "confidence": None}
                )
                item_data[item_field] = {
                    "content": item_field_data.get("content"),
                    "confidence": item_field_data.get("confidence"),
                }
            items.append(item_data)
        invoice_data["Items"] = items
        return invoice_data

    def _generate_docs_single(self, result: Any) -> Iterator[LangchainDocument]:
        yield LangchainDocument(page_content=result.content, metadata={})

    def load(self, result: Any) -> List[LangchainDocument]:
        """Load given path as pages."""
        return list(self._generate_docs_single(result))
