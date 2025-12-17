import logging
import os
from typing import Any, Dict, List, Optional

import pymongo
from dotenv import load_dotenv
from pymongo.errors import ConfigurationError, DuplicateKeyError, PyMongoError

# For MONGODB-OIDC support
try:
    from pymongo.auth_oidc import (
        OIDCCallback,
        OIDCCallbackContext,
        OIDCCallbackResult,
    )
    from azure.identity import DefaultAzureCredential

    HAS_OIDC_SUPPORT = True
except ImportError:
    HAS_OIDC_SUPPORT = False

# Initialize logging
logger = logging.getLogger(__name__)


class CosmosDBMongoCoreManager:
    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initialize the CosmosDBMongoCoreManager for connecting to Cosmos DB using MongoDB API.
        Supports both standard credentials and MONGODB-OIDC authentication.
        """
        load_dotenv()
        # Prefer SRV string; allow explicit non-SRV override when DNS is restricted.
        connection_string = (
            connection_string
            or os.getenv("AZURE_COSMOS_CONNECTION_STRING")
            or os.getenv("AZURE_COSMOS_CONNECTION_STRING_DIRECT")
        )
        database_name = database_name or os.getenv("AZURE_COSMOS_DATABASE_NAME")
        collection_name = collection_name or os.getenv("AZURE_COSMOS_COLLECTION_NAME")

        if not connection_string:
            raise ConfigurationError(
                "Missing Cosmos DB connection string. Set AZURE_COSMOS_CONNECTION_STRING or AZURE_COSMOS_CONNECTION_STRING_DIRECT."
            )

        # Try standard connection first
        self.client = None
        try:
            self.client = pymongo.MongoClient(connection_string)
            # Verify connection with a ping
            self.client.admin.command("ping")
            self.database = self.client[database_name]
            self.collection = self.database[collection_name]
            logger.info(
                f"Connected to Cosmos DB database: '{database_name}', collection: '{collection_name}'"
            )
            return
        except ConfigurationError as e:
            # Check if this is an OIDC auth error and we have OIDC support available
            if "MONGODB-OIDC" in str(e) and HAS_OIDC_SUPPORT:
                logger.info(
                    "Detected MONGODB-OIDC auth requirement. Setting up Entra ID token."
                )
                try:
                    self.client = self._create_oidc_client(connection_string)
                    self.database = self.client[database_name]
                    self.collection = self.database[collection_name]
                    logger.info(
                        f"Connected to Cosmos DB (OIDC) database: '{database_name}', collection: '{collection_name}'"
                    )
                    return
                except Exception as oidc_error:
                    logger.error(
                        f"Failed to connect with MONGODB-OIDC: {oidc_error}. "
                        "Ensure you are authenticated with Azure CLI (az login) or have AZURE_TENANT_ID, "
                        "AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET set."
                    )
                    raise
            else:
                # Helpful diagnostics for non-OIDC configuration errors
                logger.error(
                    "Failed to connect to Cosmos DB (configuration error: %s). "
                    "If you are in an environment without DNS SRV resolution, "
                    "set AZURE_COSMOS_CONNECTION_STRING_DIRECT to a non-SRV Mongo connection string.",
                    e,
                )
                direct = os.getenv("AZURE_COSMOS_CONNECTION_STRING_DIRECT")
                if direct and connection_string.startswith("mongodb+srv"):
                    logger.info(
                        "Retrying Cosmos DB connection with AZURE_COSMOS_CONNECTION_STRING_DIRECT."
                    )
                    self.client = pymongo.MongoClient(direct)
                    self.database = self.client[database_name]
                    self.collection = self.database[collection_name]
                    return
                raise
        except PyMongoError as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            raise

    @staticmethod
    def _create_oidc_client(connection_string: str):
        """
        Create a MongoClient with MONGODB-OIDC authentication using Azure credentials.
        Uses pymongo's native OIDCCallback with DefaultAzureCredential for token management.
        """
        if not HAS_OIDC_SUPPORT:
            raise ImportError(
                "OIDC support requires pymongo>=4.2 with auth_oidc and azure-identity. "
                "Install with: pip install 'pymongo>=4.2' azure-identity"
            )

        # Create Azure credential provider
        credential = DefaultAzureCredential()

        # Create pymongo's OIDCCallback with Azure token provider
        class AzureIdentityTokenCallback(OIDCCallback):
            def __init__(self, credential):
                self.credential = credential

            def fetch(
                self, context: OIDCCallbackContext
            ) -> OIDCCallbackResult:
                token = self.credential.get_token(
                    "https://mongo.cosmos.azure.com/.default"
                ).token
                return OIDCCallbackResult(access_token=token)

        # Create client with OIDC callback
        callback = AzureIdentityTokenCallback(credential)
        return pymongo.MongoClient(
            connection_string,
            authMechanism="MONGODB-OIDC",
            authMechanismProperties={"OIDC_CALLBACK": callback},
        )

    def insert_document(self, document: Dict[str, Any]) -> Optional[Any]:
        """
        Insert a document into the collection. If the document with the same _id already exists, it will raise a DuplicateKeyError.
        :param document: The document data to insert.
        :return: The inserted document's ID or None if an error occurred.
        """
        try:
            result = self.collection.insert_one(document)
            logger.info(f"Inserted document with _id: {result.inserted_id}")
            return result.inserted_id
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error while inserting document: {e}")
            return None
        except PyMongoError as e:
            logger.error(f"Failed to insert document: {e}")
            return None

    def upsert_document(
        self, document: Dict[str, Any], query: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Upsert (insert or update) a document into the collection. If a document matching the query exists, it will update the document, otherwise it inserts a new one.
        :param document: The document data to upsert.
        :param query: The query to find an existing document to update.
        :return: The upserted document's ID if a new document is inserted, None otherwise.
        """
        try:
            # Try updating the document; insert if it doesn't exist
            result = self.collection.update_one(query, {"$set": document}, upsert=True)
            if result.upserted_id:
                logger.info(f"Upserted document with _id: {result.upserted_id}")
                return result.upserted_id
            else:
                logger.info(f"Updated document matching query: {query}")
                return None
        except PyMongoError as e:
            logger.error(f"Failed to upsert document: {e}")
            return None

    def read_document(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Read a document from the collection based on a query.
        :param query: The query to match the document.
        :return: The matched document or None if not found.
        """
        try:
            document = self.collection.find_one(query)
            if document:
                logger.info(f"Found document: {document}")
            else:
                logger.warning("No document found for the given query.")
            return document
        except PyMongoError as e:
            logger.error(f"Failed to read document: {e}")
            return None

    def query_documents(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Query multiple documents from the collection based on a query.
        :param query: The query to match documents.
        :return: A list of matching documents.
        """
        try:
            documents = list(self.collection.find(query))
            logger.info(f"Found {len(documents)} documents matching the query.")
            return documents
        except PyMongoError as e:
            logger.error(f"Failed to query documents: {e}")
            return []

    def document_exists(self, query: Dict[str, Any]) -> bool:
        """
        Check if a document exists in the collection based on a query.
        :param query: The query to match the document.
        :return: True if the document exists, False otherwise.
        """
        try:
            exists = self.collection.count_documents(query) > 0
            if exists:
                logger.info(f"Document matching query {query} exists.")
            else:
                logger.info(f"Document matching query {query} does not exist.")
            return exists
        except PyMongoError as e:
            logger.error(f"Failed to check document existence: {e}")
            return False

    def delete_document(self, query: Dict[str, Any]) -> bool:
        """
        Delete a document from the collection based on a query.
        :param query: The query to match the document to delete.
        :return: True if a document was deleted, False otherwise.
        """
        try:
            result = self.collection.delete_one(query)
            if result.deleted_count > 0:
                logger.info(f"Deleted document matching query: {query}")
                return True
            else:
                logger.warning(f"No document found to delete for query: {query}")
                return False
        except PyMongoError as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    def close_connection(self):
        """Close the connection to Cosmos DB."""
        self.client.close()
        logger.info("Closed the connection to Cosmos DB.")
