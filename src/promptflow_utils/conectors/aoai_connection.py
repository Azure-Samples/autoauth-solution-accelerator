import argparse
import logging
import os
import subprocess
from typing import Optional

from dotenv import load_dotenv


def create_openai_connection(
    api_key: str, api_base: str, connection_name: str = "open_ai_connection"
) -> Optional[str]:
    """
    Creates a connection using a subprocess call.

    Args:
    api_key (str): The API key for OpenAI.
    api_base (str): The base URL for the API.
    connection_name (str): The name for the connection. Default is 'open_ai_connection'.

    Returns:
    Optional[str]: The output of the subprocess command or None if an error occurs.
    """
    command = f"pf connection create --file ./src/build_your_own_copilot/connect_azure_openai.yaml --set api_key={api_key} api_base={api_base} --name {connection_name}"

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
    parser = argparse.ArgumentParser(description="Create OpenAI connection.")
    parser.add_argument(
        "--name",
        default="open_ai_connection",
        help="The name for the connection.",
        required=False,
    )
    args = parser.parse_args()

    # Load environment variables from .env file
    load_dotenv()

    # Retrieve API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    api_base = os.getenv("OPENAI_API_ENDPOINT")

    # Check if the API key is available
    if api_key is None:
        logging.error("API key not found. Please set OPENAI_API_KEY in your .env file.")
        return

    # Run the connection creation function
    result = create_openai_connection(api_key, api_base, args.name)

    # Log the result
    if result:
        logging.info("Connection created successfully.")
        logging.info(result)
    else:
        logging.error("Failed to create connection.")


if __name__ == "__main__":
    main()
