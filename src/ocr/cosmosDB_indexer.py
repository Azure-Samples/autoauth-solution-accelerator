import os
from typing import Any, Dict, List, Optional

from azure.cosmos import (
    ContainerProxy,
    CosmosClient,
    DatabaseProxy,
    PartitionKey,
    exceptions,
)

from utils.ml_logging import get_logger

# Initialize logging
logger = get_logger()


class CosmosDBIndexer:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        credential_id: Optional[str] = None,
        database_name: Optional[str] = None,
        container_name: Optional[str] = None,
    ):
        """
        Initialize the CosmosDBIndexer with connection details to Azure Cosmos DB.

        :param endpoint_url: Endpoint URL for the Azure Cosmos DB account.
        :param credential_id: Credential ID for the Azure Cosmos DB account.
        :param database_name: The name of the database to use.
        :param container_name: The name of the container to index data into.
        """
        try:
            self.client = CosmosClient(
                endpoint_url or os.getenv("AZURE_COSMOSDB_ENDPOINT"),
                credential=credential_id or os.getenv("AZURE_COSMOSDB_KEY"),
            )
        except Exception as e:
            raise ValueError("Failed to initialize CosmosClient") from e

        if database_name is not None:
            self.database: DatabaseProxy = self.client.get_database_client(
                database_name
            )
        if container_name is not None:
            self.container: ContainerProxy = self.database.get_container_client(
                container_name
            )

    def create_database(self, database_name: str) -> None:
        """
        Create a new database if it does not exist.

        :param database_name: The name of the database to create.
        :return: None
        """
        self.database = self.client.create_database_if_not_exists(id=database_name)
        logger.info(f"Database '{database_name}' created successfully.")

    def create_container(
        self,
        container_name: str,
        partition_key: Optional[str] = "/InvoiceId",
        throughput: Optional[int] = None,
        indexing_policy: Optional[dict] = None,
        default_ttl: Optional[int] = None,
        unique_key_policy: Optional[dict] = None,
        conflict_resolution_policy: Optional[dict] = None,
        analytical_storage_ttl: Optional[int] = None,
    ) -> None:
        """
        Create a new container if it does not exist.

        :param container_name: The name of the container to create. This is the ID of the container in Azure Cosmos DB.
        :param partition_key: The partition key to use for the container. This is used to distribute data across multiple partitions for scalability and performance. Defaults to "/InvoiceId".
        :param throughput: The provisioned throughput for this container. This is measured in Request Units (RU) and determines the cost and capacity of the container. Defaults to None, which means Azure will automatically scale the throughput.
        :param indexing_policy: The indexing policy to apply to the container. This determines how items in the container are indexed.
        :param default_ttl: Default time to live (TTL) for items in the container. If unspecified, items do not expire. This is measured in seconds.
        :param unique_key_policy: The unique key policy to apply to the container. This enforces uniqueness of one or more values in each item.
        :param conflict_resolution_policy: The conflict resolution policy to apply to the container. This determines how conflicts (when the same item is updated concurrently from different clients) are resolved.
        :param analytical_storage_ttl: Analytical store time to live (TTL) for items in the container. A value of None leaves analytical storage off and a value of -1 turns analytical storage on with no TTL.
        :return: None
        """
        # Define the container's settings
        container_settings = {
            "id": container_name,
            "partition_key": PartitionKey(path=partition_key),
        }

        # Create a new container if it does not exist
        self.container = self.database.create_container_if_not_exists(
            id=container_settings["id"],
            partition_key=container_settings["partition_key"],
            offer_throughput=throughput,
            indexing_policy=indexing_policy,
            default_ttl=default_ttl,
            unique_key_policy=unique_key_policy,
            conflict_resolution_policy=conflict_resolution_policy,
            analytical_storage_ttl=analytical_storage_ttl,
        )

        logger.info(
            f"Container '{container_name}' in database '{self.database.id}' created successfully."
        )

    def index_data(
        self, data_list: List[Dict[str, Any]], id_key: str = "InvoiceId"
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Indexes a list of data items into the specified Azure Cosmos DB container.

        This method preprocesses each provided data item, ensuring that it's in the correct format
        for Azure Cosmos DB, and then attempts to upsert the data into the container.

        :param data_list: A list of dictionaries, each representing a data item to be indexed, potentially including nested structures.
        :param id_key: The key to use for the Invoice ID in the indexed data. Defaults to 'InvoiceId'.
        :return: A list of responses from the database after indexing each data item or None if an error occurred.
        """
        responses = []
        for i, data in enumerate(data_list):
            try:
                logger.info(f"Processing data item {i+1} of {len(data_list)}")
                processed_data = self.preprocess_data(data)

                if id_key in processed_data and processed_data[id_key] not in [
                    None,
                    "null",
                ]:
                    logger.info(f"Duplicating key '{id_key}' as 'id'")
                    processed_data["id"] = processed_data[id_key]
                else:
                    logger.warning(
                        f"Data item {i+1} has a null {id_key}. Skipping this item."
                    )
                    continue

                logger.info("Upserting data item into Cosmos DB")
                response = self.container.upsert_item(processed_data)
                logger.info(
                    f"Data indexed successfully with id: {processed_data['id']}"
                )
                responses.append(response)
            except exceptions.CosmosHttpResponseError as e:
                logger.error(f"Failed to index data item {i+1}: {e}")
                responses.append(None)
            except Exception as ex:
                logger.error(
                    f"An unexpected error occurred while processing data item {i+1}: {ex}"
                )
                responses.append(None)
        logger.info(f"Final number of records indexed: {len(responses)}")
        return responses

    # TODO: Add preprocess_data method as needed
    @staticmethod
    def preprocess_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocesses the data before indexing in Azure Cosmos DB.
        :param data: The original data dictionary to be preprocessed.
        :return: A dictionary of the processed data ready for indexing.
        """
        logger.info(f"Data before preprocessing: {data}")
        processed_data = {}
        for key, value in data.items():
            if isinstance(value, dict) and "content" in value:
                value = value["content"]
                if value == "null":
                    value = None
                # elif key in ["InvoiceTotal", "TotalTax", "AmountDue"]:
                #     value = float(value.replace(",", ".")) if value else None
                elif key in ["id", "primary_key"]:
                    value = str(value)
                processed_data[key] = value
            else:
                processed_data[key] = value
        logger.info(f"Data after preprocessing: {processed_data}")
        return processed_data

    def execute_query(self, query: str):
        """
        Executes a SQL query against the Azure Cosmos DB container.

        :param query: The SQL query to execute.
        :return: The result of the query or None if an error occurred.
        """
        try:
            # Execute the query
            items = list(
                self.container.query_items(
                    query=query, enable_cross_partition_query=True
                )
            )

            if items:
                logger.info(
                    f"Query executed successfully. Retrieved {len(items)} items."
                )
                return items
            else:
                logger.warning("No data found for the given query.")
                return None
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"An error occurred: {e.message}")
            return None
