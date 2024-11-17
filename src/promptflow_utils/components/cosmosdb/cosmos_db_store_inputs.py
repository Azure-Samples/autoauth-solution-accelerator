import logging
import os
import random
from datetime import datetime
from typing import Optional

from azure.core.exceptions import AzureError
from azure.cosmos import CosmosClient
from dotenv import load_dotenv

from pipeline import tool

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Cosmos DB configuration
COSMOS_URI = os.getenv("COSMOS_URI")
COSMOS_KEY = os.getenv("COSMOS_KEY")

# Initialize the Cosmos client
client = CosmosClient(url=COSMOS_URI, credential=COSMOS_KEY)


@tool
def send_to_cosmos_db(
    chat_id: str,
    input_str: str,
    cosmos_database: str,
    cosmos_container: str,
    client: CosmosClient = client,
    user_id: Optional[str] = None,
    safety_target: Optional[str] = None,
) -> str:
    """
    Send a string to a specified Cosmos DB container.

    Args:
        chat_id (str): The chat ID associated with the string to be sent.
        user_id (str, optional): The user ID associated with the string to be sent. If not provided, an 8-digit random ID will be generated.
        input_str (str): The string to be sent.
        cosmos_database (str): The name of the Cosmos DB database.
        cosmos_container (str): The name of the Cosmos DB container.
        client (CosmosClient, optional): The Cosmos DB client. Defaults to the globally defined client.
        safety_target_alert (str, optional): A string indicating the safety target alert being triggered. Defaults to None.

    Returns:
        str: A message indicating the result of the operation.
    """
    try:
        # Get a reference to the database
        database = client.get_database_client(cosmos_database)
        # Get a reference to the container
        container = database.get_container_client(cosmos_container)

        # Get the current time in ISO 8601 format with Z indicating UTC time
        current_time = datetime.utcnow().isoformat() + "Z"

        # Generate an 8-digit random user ID if one is not provided
        if user_id is None:
            user_id = "".join(random.choices("0123456789", k=8))

        # Define the data to be stored
        data = {
            "id": user_id,
            "ChatId": chat_id,
            "content": input_str,
            "timestamp": current_time,
            "safety_target": safety_target,
        }

        # Insert the item into the container
        container.upsert_item(data)

        return f"Data with chat ID {chat_id}, user ID {user_id}, and timestamp {current_time} sent to Cosmos DB successfully in database '{cosmos_database}' and container '{cosmos_container}'."

    except AzureError as e:
        # Handle the Azure exception
        logger.error(f"An error occurred: {str(e)}")
        return f"An error occurred: {str(e)}"


def _check_databases(client: CosmosClient) -> None:
    """
    List the databases and their containers in the Cosmos DB account.

    Args:
        client (CosmosClient): The Cosmos DB client.
    """
    # List the databases
    databases = list(client.list_databases())
    if not databases:
        print("No databases found in the Cosmos account.")
        return

    for database in databases:
        print(f"Database Id: {database['id']}")
        db_client = client.get_database_client(database["id"])

        # List the containers for each database
        containers = list(db_client.list_containers())
        if not containers:
            print(f"  No containers found in the database '{database['id']}'.")
        for container in containers:
            print(f"  Container Id: {container['id']}")
