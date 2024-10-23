import argparse
import logging
import os
import subprocess
from typing import Optional

from dotenv import load_dotenv


def create_cognitive_search_connection(
    api_key: str, connection_name: str = "cognitive_search_connection"
) -> Optional[str]:
    """
    Creates a Cognitive Search connection using a subprocess call.

    Args:
    api_key (str): The API key for Cognitive Search.
    connection_name (str): The name for the connection. Default is 'cognitive_search_connection'.

    Returns:
    Optional[str]: The output of the subprocess command or None if an error occurs.
    """
    command = f"pf connection create -f ./src/build_your_own_copilot/connect_azure_search.yaml --set api_key={api_key} --name {connection_name}"

    try:
        result = subprocess.run(
            command, shell=True, check=True, text=True, capture_output=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error occurred: {e}")
        return None


def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Create Cognitive Search connection.")
    parser.add_argument(
        "--name",
        default="cognitive_search_connection",
        help="The name for the connection.",
        required=False,
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Retrieve API key and endpoint from environment variables
    api_key = os.getenv("AZURE_COGNITIVE_SEARCH_API_KEY")

    # Check if the API key and endpoint are available
    if api_key is None:
        logging.error(
            "API key or endpoint not found. Please set AZURE_COGNITIVE_SEARCH_API_KEY in your .env file."
        )
        return

    # Run the connection creation function
    result = create_cognitive_search_connection(api_key, args.name)

    # Log the result
    if result:
        logging.info("Cognitive Search connection created successfully.")
        logging.info(result)
    else:
        logging.error("Failed to create Cognitive Search connection.")


if __name__ == "__main__":
    main()
