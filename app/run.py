import argparse
import asyncio
import os
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Union

import dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryType,
    VectorizableTextQuery,
)
from azure.storage.blob import BlobServiceClient
from colorama import Fore, Style, init

from src.aoai.aoai_helper import AzureOpenAIManager
from app.components.prompts import (
    SYSTEM_PROMPT_NER,
    SYSTEM_PROMPT_PRIOR_AUTH,
    SYSTEM_PROMPT_QUERY_EXPANSION,
    create_prompt_pa,
    create_prompt_query_expansion,
    USER_PROMPT_NER,
)
from src.extractors.pdf_data_extractor import OCRHelper
from src.ocr.document_intelligence import AzureDocumentIntelligenceManager
from utils.ml_logging import get_logger

# Initialize colorama
init(autoreset=True)

# Set up logger
logger = get_logger()

# Load environment variables
dotenv.load_dotenv(".env")

# Generate a unique ID for the case
import uuid

def generate_unique_id() -> str:
    """
    Generate an 8-character unique ID.

    Returns:
        str: An 8-character unique value.
    """
    unique_id = str(uuid.uuid4())
    eight_char_unique_value = unique_id[:8]
    return eight_char_unique_value


# Initialize session state variables
session_state = {
    "azure_openai_client_4o": AzureOpenAIManager(
        completion_model_name="AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
    ),
    "search_client": SearchClient(
        endpoint=os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"],
        index_name=os.environ["AZURE_AI_SEARCH_INDEX_NAME"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_SEARCH_ADMIN_KEY"]),
    ),
    "container_name": "pre-auth-policies",
    "conversation_id": generate_unique_id(),
    "conversation_history": {},
}

# Correctly set the temp_dir as a string
session_state['temp_dir'] = os.path.join(
    r"C:\Users\pablosal\Desktop\gbb-ai-hls-factory-prior-auth\utils\temp",
    session_state["conversation_id"]
)

# Ensure the temp_dir exists
os.makedirs(session_state['temp_dir'], exist_ok=True)

def locate_policy(api_response_gpt4o: Dict[str, Any]) -> str:
    """
    Locate the policy based on the optimized query from the AI response.

    :param api_response_gpt4o: The AI response containing the optimized query.
    :return: The location of the policy or a message indicating no results were found.
    """
    search_client = session_state["search_client"]
    try:
        optimized_query = api_response_gpt4o["response"]["optimized_query"]
        vector_query = VectorizableTextQuery(
            text=optimized_query, k_nearest_neighbors=5, fields="vector", weight=0.5
        )

        results = search_client.search(
            search_text=optimized_query,
            vector_queries=[vector_query],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="my-semantic-config",
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=5,
        )

        first_result = next(iter(results), None)
        if first_result:
            parent_path = first_result.get("parent_path", "Path not found")
            return parent_path
        else:
            return "No results found"
    except Exception as e:
        logger.error(f"Error locating policy: {e}")
        return "Error locating policy"


def process_uploaded_files(uploaded_files: List[str]) -> str:
    """
    Process uploaded files and extract images.

    :param uploaded_files: List of file paths to the uploaded files.
    :return: Path to the temporary directory containing processed images.
    """
    ocr_data_extractor_helper = OCRHelper(
        container_name=session_state["container_name"]
    )
    temp_dir = session_state['temp_dir']

    try:
        for file_path in uploaded_files:
            logger.info(f"Processing file: {file_path}")
            ocr_data_extractor_helper.extract_images_from_pdf(
                input_path=file_path, output_path=temp_dir
            )
        logger.info(f"Files processed and images extracted to: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"Failed to process files: {e}")
        return temp_dir


def get_policy_text_from_blob(blob_url: str) -> str:
    """
    Download the blob content from the given URL and extract text.

    :param blob_url: The URL of the blob.
    :return: The extracted text from the document.
    """
    document_intelligence_client = AzureDocumentIntelligenceManager()
    try:
        parsed_url = urllib.parse.urlparse(blob_url)
        blob_name = "/".join(parsed_url.path.split("/")[2:])
        container_name = parsed_url.path.split("/")[1]
        blob_service_client = BlobServiceClient.from_connection_string(
            os.environ["BLOB_CONNECTION_STRING"]
        )
        blob_client = blob_service_client.get_blob_client(
            container=container_name, blob=blob_name
        )
        blob_content = blob_client.download_blob().readall()
        logger.info(f"Blob content downloaded successfully from {blob_url}")
    except Exception as e:
        logger.error(f"Failed to download blob content from {blob_url}: {e}")
        return ""

    try:
        policy_text = document_intelligence_client.analyze_document(
            document_input=blob_content,
            model_type="prebuilt-layout",
            output_format="markdown",
        )
        logger.info(f"Document analyzed successfully for blob {blob_url}")
        return policy_text.content
    except Exception as e:
        logger.error(f"Failed to analyze document for blob {blob_url}: {e}")
        return ""


def find_all_files(root_folder: str, extensions: Union[List[str], str]) -> List[str]:
    """
    Recursively find all files with specified extensions under the root folder.

    :param root_folder: The root folder to search for files.
    :param extensions: List of file extensions to search for (e.g., ['png', 'jpg']).
    :return: List of full paths to the found files.
    """
    if isinstance(extensions, str):
        extensions = [extensions]

    files_list = []
    root_folder_path = Path(root_folder).resolve()

    for root, _, files in os.walk(root_folder_path):
        for file in files:
            if any(file.lower().endswith(f".{ext}") for ext in extensions):
                files_list.append(str(Path(root) / file))
    logger.info(f"Found {len(files_list)} files with extensions {extensions}")
    return files_list


async def generate_ai_response(
    user_prompt: str, system_prompt: str, image_paths: List[str] = None, response_format: str = 'json_object'
) -> Dict[str, Any]:
    """
    Generate AI response using OpenAI's API.

    :param user_prompt: The user prompt to send to the AI.
    :param system_prompt: The system prompt to set the context for the AI.
    :param image_paths: List of image file paths to include in the AI request.
    :return: The AI response as a dictionary.
    """
    try:
        response = await session_state[
            "azure_openai_client_4o"
        ].generate_chat_response(
            query=user_prompt,
            system_message_content=system_prompt,
            image_paths=image_paths,
            conversation_history=[],
            max_tokens=3000,
            response_format=response_format

        )
        return response
    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return {}


def chat_interface() -> None:
    """
    Chat interface allowing interaction between the user and the AI.

    This function creates a terminal-based chat interface, processes user inputs,
    and displays AI responses, including processing of uploaded documents.
    """
    print(Fore.CYAN + "\nWelcome to the Prior Authorization Assistant!")
    print("Type 'exit' to quit.\n")

    conversation_history: List[Dict[str, str]] = []

    try:
        # Allow the user to input the directory up to three times
        max_attempts = 3
        attempts = 0

        while attempts < max_attempts:
            try:
                # Ask the user for the directory of files to process
                input_dir = input(
                    Fore.GREEN + "Enter the path to the directory containing files to process: "
                )
                process_documents_flow(input_dir)

                # If processing is successful, break out of the loop
                print(Fore.GREEN + "Documents processed successfully.")
                break
            except Exception as e:
                # Increment the attempt counter
                attempts += 1

                # Print the error message
                print(Fore.RED + f"Error: {e}")

                # If the maximum number of attempts is reached, print a message and exit
                if attempts == max_attempts:
                    print(Fore.RED + "Maximum number of attempts reached. Exiting.")
                    return

        # After processing, display the final determination
        final_response = session_state["conversation_history"].get("final_determination")
        if final_response:
            print(
                Fore.MAGENTA
                + "\nFinal Determination:\n"
                + final_response.get("data", "")
            )
        else:
            print(Fore.RED + "No final determination available.")

        print(Fore.CYAN + "\nYou can now interact with the assistant.")
        while True:
            user_input = input(Fore.GREEN + "You: ")
            if user_input.lower() == "exit":
                print(Fore.CYAN + "Goodbye!")
                break

            conversation_history.append({"role": "user", "content": user_input})

            # Store user input in session state
            store_output_in_memory({"user_input": user_input}, step="user_input")

            # Process user input and generate AI response
            ai_response = asyncio.run(
                generate_ai_response(
                    user_prompt=user_input,
                    system_prompt=SYSTEM_PROMPT_NER,
                    image_paths=[],
                )
            )

            ai_content = ai_response.get("response", {}).get("text", "")
            print(Fore.YELLOW + "Assistant: " + ai_content)

            conversation_history.append({"role": "assistant", "content": ai_content})

            # Store AI response in session state
            store_output_in_memory({"ai_response": ai_content}, step="ai_response")
    except KeyboardInterrupt:
        print(Fore.CYAN + "\nChat session ended by user.")
    except Exception as e:
        logger.error(f"Error in chat interface: {e}")


def process_documents_flow(input_dir: str) -> None:
    """
    Process documents as per the pipeline flow and store the outputs in memory.

    :param input_dir: Directory containing files to process.
    """
    uploaded_files = find_all_files(input_dir, ["pdf"])

    if uploaded_files:
        try:
            temp_dir = process_uploaded_files(uploaded_files)
            extensions = ["png"]
            pa_files_images = find_all_files(temp_dir, extensions)

            # Generate AI response for NER
            print(Fore.CYAN + "\nAnalyzing clinical information...")
            api_response_gpt4o = asyncio.run(
                generate_ai_response(
                    USER_PROMPT_NER, SYSTEM_PROMPT_NER, pa_files_images
                )
            )

            # Store NER response in memory
            store_output_in_memory(api_response_gpt4o, step="NER_response")

            clinical_info = api_response_gpt4o["response"].get("Clinical Information")
            if clinical_info:
                system_prompt_query_expansion = create_prompt_query_expansion(
                    clinical_info
                )
                # Generate AI response for query expansion
                print(Fore.CYAN + "Expanding query and searching for policy...")
                api_response_search = asyncio.run(
                    generate_ai_response(
                        system_prompt_query_expansion,
                        SYSTEM_PROMPT_QUERY_EXPANSION,
                        None,
                    )
                )

                # Store query expansion response in memory
                store_output_in_memory(api_response_search, step="query_expansion")

                # Locate the policy
                policy_location = locate_policy(api_response_search)
                if (
                    policy_location != "No results found"
                    and policy_location != "Error locating policy"
                ):
                    policy_text = get_policy_text_from_blob(policy_location)

                    # Store policy text in memory
                    store_output_in_memory(
                        {"policy_location": policy_location, "policy_text": policy_text},
                        step="policy_retrieval",
                    )

                    if policy_text:
                        user_prompt_pa = create_prompt_pa(clinical_info, policy_text)
                        # Generate final AI response
                        print(Fore.CYAN + "Generating final determination...")
                        api_response_final = asyncio.run(
                            generate_ai_response(
                                user_prompt_pa,
                                SYSTEM_PROMPT_PRIOR_AUTH,
                                pa_files_images,
                                response_format='text'
                            )
                        )
                        print(
                            Fore.MAGENTA + "\nFinal Determination:\n" + api_response_final["response"]
                        )

                        # Store final determination in memory
                        store_output_in_memory(
                            {"final_determination": api_response_final["response"]},
                            step="final_determination",
                        )
                    else:
                        print(Fore.RED + "Policy text not found.")
                        store_output_in_memory(
                            {"error": "Policy text not found."}, step="error"
                        )
                else:
                    print(Fore.RED + "Policy not found.")
                    store_output_in_memory(
                        {"error": "Policy not found."}, step="error"
                    )
            else:
                print(Fore.RED + "Clinical Information not found in AI response.")
                store_output_in_memory(
                    {"error": "Clinical Information not found."}, step="error"
                )
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            store_output_in_memory({"error": str(e)}, step="error")
    else:
        print(Fore.RED + "No files found in the input directory.")


def store_output_in_memory(data: Dict[str, Any], step: str) -> None:
    """
    Store the given data in the conversation history dictionary.

    :param data: The data to store.
    :param step: The step identifier to categorize the data.
    """
    conversation_id = session_state["conversation_id"]
    if conversation_id not in session_state["conversation_history"]:
        session_state["conversation_history"][conversation_id] = {}

    session_state["conversation_history"][conversation_id][step] = {"data": data}


def main() -> None:
    """
    Main function to run the application.

    This function initializes the chat interface and starts the interaction
    between the user and the AI assistant.
    """
    try:
        chat_interface()
    except Exception as e:
        logger.error(f"Application encountered an error: {e}")


if __name__ == "__main__":
    main()