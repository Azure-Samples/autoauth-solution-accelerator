import base64
import os
from typing import Any, Dict, Iterator, List, Optional, Union

from azure.ai.documentintelligence import DocumentIntelligenceClient, models
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, Document
from azure.core.credentials import AzureKeyCredential
from azure.core.polling import LROPoller

# from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from langchain_core.documents import Document as LangchainDocument

from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger

# Initialize logging
logger = get_logger()


class AzureDocumentIntelligenceManager:
    """
    A class to interact with Azure's Document Analysis Client.

    Attributes:
        azure_endpoint (str): Endpoint URL for Azure's Document Analysis Client.
        azure_key (str): API key for Azure's Document Analysis Client.
        blob_manager (Optional[AzureBlobManager]): Instance of AzureBlobManager for blob operations.
    """

    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        azure_key: Optional[str] = None,
        storage_account_name: Optional[str] = None,
        container_name: Optional[str] = None,
        account_key: Optional[str] = None,
    ):
        """
        Initialize the class with configurations for Azure's Document Analysis Client.

        Args:
            azure_endpoint (Optional[str]): Endpoint URL for Azure's Document Analysis Client.
            azure_key (Optional[str]): API key for Azure's Document Analysis Client.
            storage_account_name (Optional[str]): Name of the Azure Storage account.
            container_name (Optional[str]): Name of the blob container.
            account_key (Optional[str]): Storage account key for authentication.
        """
        # Load environment variables if not provided
        load_dotenv()
        self.azure_endpoint = azure_endpoint or os.getenv(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
        )
        self.azure_key = azure_key or os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

        # Validate required configurations for Document Analysis Client
        if not self.azure_endpoint:
            raise ValueError(
                "Azure endpoint and key must be provided either as parameters or in environment variables."
            )

        # credential = DefaultAzureCredential()
        # if self.azure_key:
        #   credential = AzureKeyCredential(self.azure_key)

        self.document_analysis_client = DocumentIntelligenceClient(
            endpoint=self.azure_endpoint,
            credential=AzureKeyCredential(self.azure_key),
            api_version="2024-11-30",
            headers={"x-ms-useragent": "langchain-parser/1.0.0"},
            polling_interval=30,
        )

        # Initialize AzureBlobManager only if all required parameters are provided
        if storage_account_name and container_name and account_key:
            self.blob_manager = AzureBlobManager(
                storage_account_name=storage_account_name,
                container_name=container_name,
                account_key=account_key,
            )
        else:
            # self.blob_manager = None
            self.blob_manager = AzureBlobManager(
                storage_account_name=storage_account_name, container_name=container_name
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
                content_bytes = self.blob_manager.download_blob_to_bytes(document_input)
                try:
                    analyze_request = AnalyzeDocumentRequest(bytes_source=content_bytes)
                    poller = self.document_analysis_client.begin_analyze_document(
                        model_id=model_type,
                        analyze_request=analyze_request,
                        pages=pages,
                        locale=locale,
                        string_index_type=string_index_type,
                        features=features,
                        query_fields=query_fields,
                        output_content_format=output_format
                        if output_format
                        else "text",
                        content_type=content_type,
                        **kwargs,
                    )
                except Exception as e:
                    logger.error(f"Error analyzing document from blob URL: {e}")
                    raise
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
