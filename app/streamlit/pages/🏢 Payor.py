# Load environment variables
import dotenv
import streamlit as st
import asyncio
import uuid
from src.app.utils.benchmarkbuddy import configure_chatbot
from src.aoai.aoai_helper import AzureOpenAIManager
import urllib.parse
from azure.storage.blob import BlobServiceClient
from src.ocr.document_intelligence import AzureDocumentIntelligenceManager
from typing import List, Union
from utils.ml_logging import get_logger
from pathlib import Path
import os
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType, QueryAnswerType
from azure.core.credentials import AzureKeyCredential
import tempfile
import os
from src.app.utils.prompts import (SYSTEM_PROMPT_NER, 
                                   USER_PROMPT_NER,
                                   SYSTEM_PROMPT_QUERY_EXPANSION,
                                   create_prompt_query_expansion,
                                   create_prompt_pa,
                                   SYSTEM_PROMPT_PRIOR_AUTH
                                   )
                                   
from src.app.utils.policy import POLICY
from src.app.utils.determination import DETERMINATION

# Set up logger
logger = get_logger()

# Load environment variables if not already loaded
dotenv.load_dotenv(".env")

from src.extractors.pdf_data_extractor import OCRHelper

# Define session variables and initial values
session_vars = ["conversation_history", "ai_response", "chat_history", "messages", "azure_openai_client_4o", "uploaded_files", "search_client"]
initial_values = {
    "conversation_history": [],
    "ai_response": "",
    "chat_history": [],
    "container_name": "pre-auth-policies",
    "disable_chatbot": True,
    "messages": [
        {
            "role": "assistant",
            "content": "Hey, this is your AI assistant. Please look at the AI request submit and let's work together to make your content shine!",
        }
    ],
    "azure_openai_client_4o": AzureOpenAIManager(completion_model_name='AZURE_OPENAI_CHAT_DEPLOYMENT_ID'),
    "uploaded_files": [],
    "search_client": SearchClient(
        endpoint=os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"],
        index_name=os.environ["AZURE_AI_SEARCH_INDEX_NAME"],
        credential=AzureKeyCredential(os.environ["AZURE_AI_SEARCH_ADMIN_KEY"]),
    )
}

# Initialize session state variables
for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = initial_values.get(var, None)

# Initialize session state variables
for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = initial_values.get(var, None)

st.set_page_config(
    page_title="SmartPA",
    page_icon="✨",
)

def locate_policy(api_response_gpt4o: dict) -> str:
    """
    Locate the policy based on the optimized query from the AI response.

    Args:
        api_response_gpt4o (dict): The AI response containing the optimized query.

    Returns:
        str: The location of the policy or a message indicating no results were found.
    """

        # Initialize the search client if not already initialized
    if "search_client" not in st.session_state:
        st.session_state["search_client"] = SearchClient(
            endpoint=os.environ["AZURE_AI_SEARCH_SERVICE_ENDPOINT"],
            index_name=os.environ["AZURE_AI_SEARCH_INDEX_NAME"],
            credential=AzureKeyCredential(os.environ["AZURE_AI_SEARCH_ADMIN_KEY"]),
        )

    search_client = st.session_state['search_client']

    # Create the vector query
    vector_query = VectorizableTextQuery(
        text=api_response_gpt4o['response']['optimized_query'],
        k_nearest_neighbors=5,
        fields="vector",
        weight=0.5
    )

    # Perform the search
    results = search_client.search(
        search_text=api_response_gpt4o['response']['optimized_query'],
        vector_queries=[vector_query],
        query_type=QueryType.SEMANTIC,
        semantic_configuration_name='my-semantic-config',
        query_caption=QueryCaptionType.EXTRACTIVE,
        query_answer=QueryAnswerType.EXTRACTIVE,
        top=5
    )

    # Extract the parent path from the first result
    try:
        first_result = next(iter(results))
        parent_path = first_result.get('parent_path', 'Path not found')
        return parent_path
    except StopIteration:
        return 'No results found'


def process_uploaded_files(uploaded_files: List[st.runtime.uploaded_file_manager.UploadedFile]) -> str:
    if "container_name" not in st.session_state:
        st.session_state.container_name = "pre-auth-policies"
    ocr_data_extractor_helper = OCRHelper(container_name=st.session_state.container_name)

    try:
        # Create a new folder with a random ID under the specified directory
        base_temp_dir = "C:/Users/pablosal/Desktop/gbb-ai-hls-factory-prior-auth/utils/temp"
        random_id = str(uuid.uuid4())
        temp_dir = os.path.join(base_temp_dir, random_id)
        os.makedirs(temp_dir, exist_ok=True)
        logger.info(f"Created temporary directory at {temp_dir}")

        for uploaded_file in uploaded_files:
            try:
                # Save the uploaded file to the temporary directory
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                logger.info(f"Saved uploaded file to {file_path}")

                # Extract images from the uploaded file
                ocr_data_extractor_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=temp_dir
                )
                logger.info(f"Extracted images from {file_path}")

            except Exception as e:
                logger.error(f"Failed to process file {uploaded_file.name}: {e}")

        return temp_dir

    except Exception as e:
        logger.error(f"Failed to create temporary directory or process files: {e}")
        return ""

def get_policy_text_from_blob(blob_url: str) -> str:
    """
    Download the blob content from the given URL and analyze the document to extract text.

    Args:
        blob_url (str): The URL of the blob.

    Returns:
        str: The extracted text from the document.
    """
    # Initialize the document intelligence client if not already initialized
    if "document_intelligence_client" not in st.session_state:
        st.session_state["document_intelligence_client"] = AzureDocumentIntelligenceManager()

    document_intelligence_client = st.session_state["document_intelligence_client"]
    try:
        # Blob URL
        blob_url = "https://storagefactoryeastus.blob.core.windows.net/pre-auth-policies/policies_ocr/001_inflammatory_Conditions.pdf"

        # Parse the URL to extract the blob name
        parsed_url = urllib.parse.urlparse(blob_url)
        blob_name = '/'.join(parsed_url.path.split('/')[2:])  # Extract the blob name correctly

        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(os.environ["BLOB_CONNECTION_STRING"])

        # Extract the container name from the URL
        container_name = parsed_url.path.split('/')[1]

        # Log the container name and blob name for debugging
        print(f"Container Name: {container_name}")
        print(f"Blob Name: {blob_name}")
    
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_content = blob_client.download_blob().readall()
        print("Blob content downloaded successfully.")
    except Exception as e:
        print(f"Failed to download blob content: {e}")
        return POLICY

    # Use the blob content with the document intelligence client
    model_type = "prebuilt-layout"

    try:
        policy_text = document_intelligence_client.analyze_document(
            document_input=blob_content,
            model_type=model_type,
            output_format="markdown",
            features=["OCR_HIGH_RESOLUTION"],
            # pages="1-4",
        )
        return policy_text.content
    except Exception as e:
        print(f"Failed to analyze document: {e}")
        return POLICY

def find_all_files(root_folder: str, extensions: Union[List[str], str]) -> List[str]:
    """
    Recursively finds all files with specified extensions under the specified root folder, including subfolders.

    Args:
        root_folder (str): The root folder to search for files.
        extensions (Union[List[str], str]): A list of file extensions to search for (e.g., ['jpeg', 'jpg', 'png', 'pdf']).

    Returns:
        List[str]: A list of full paths to the found files.
    """
    if isinstance(extensions, str):
        extensions = [extensions]

    extensions = [ext.lower() for ext in extensions]
    files_list = []
    root_folder_path = Path(root_folder).resolve()

    logger.info(f"Searching for files in: {root_folder_path}")
    logger.info(f"File extensions to search for: {extensions}")

    for root, _, files in os.walk(root_folder_path):
        for file in files:
            if any(file.lower().endswith(f".{ext}") for ext in extensions):
                full_path = Path(root) / file
                files_list.append(str(full_path.resolve()))
                logger.info(f"Found file: {full_path.resolve()}")
    
    logger.info(f"Found {len(files_list)} files.")
    logger.info(f"Files found: {files_list}")

    return files_list

def configure_sidebar():
    # Sidebar layout for initial submission
    with st.sidebar:
        st.markdown("")

        st.markdown(
            """
            ## Welcome to the SmartPA!
        
            Our AI-powered tool streamlines the prior authorization process by analyzing your documents and providing a clinical determination based on policy criteria. 📄✨
        
            ### How it works:
            1. **Upload Documents**: Attach all relevant files, including text files, PDFs, images, and clinical notes. 📚
            2. **Submit for Analysis**: Click 'Submit to AI' and let our AI handle the rest. You'll receive a comprehensive clinical determination. 🎩
        
            Ready to get started? Let's make prior authorization effortless! 🚀
            """
        )

        uploaded_files = st.sidebar.file_uploader(
                "Upload documents",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "pdf",
                    "ppt",
                    "pptx",
                    "doc",
                    "docx",
                    "mp3",
                    "wav",
                ],
                accept_multiple_files=True,
                help="Upload the documents you want the AI to analyze. You can upload multiple documents of types PNG, JPG, JPEG, and PDF.",
            )
        
        # Store uploaded files in session state
        if uploaded_files:
            st.session_state["uploaded_files"] = uploaded_files

SYSTEM_MESSAGE_LATENCY = ""                  

def initialize_chatbot() -> None:
    """
    Initialize a chatbot interface for user interaction with enhanced features.
    """
    st.markdown(
        "<h4 style='text-align: center;'>PriorBuddy 🤖</h4>",
        unsafe_allow_html=True,
    )

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": (
                "🚀 Ask away! I am all ears and ready to dive into your queries. "
                "I'm here to make sense of the numbers from your benchmarks and support you during your analysis! 😄📊"
            ),
        }
    ]
    if "messages" not in st.session_state:
        st.session_state.messages = [
        {
            "role": "system",
            "content": f"{SYSTEM_MESSAGE_LATENCY}",
        },
        {
            "role": "assistant",
            "content": (
                "🚀 Ask away! I am all ears and ready to dive into your queries. "
                "I'm here to make sense of the numbers from your benchmarks and support you during your analysis! 😄📊"
            ),
        },
    ]

    respond_conatiner = st.container(height=400)

    with respond_conatiner:
        for message in st.session_state.chat_history:
            role = message["role"]
            content = message["content"]
            avatar_style = "🧑‍💻" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar_style):
                st.markdown(
                    f"<div style='padding: 10px; border-radius: 5px;'>{content}</div>",
                    unsafe_allow_html=True,
                )
    
    warning_issue_performance = st.empty()
    if st.session_state.get("azure_openai_manager") is None:
        warning_issue_performance.warning(
            "Oops! It seems I'm currently unavailable. 😴 Please ensure the LLM is configured correctly in the Benchmark Center and Buddy settings. Need help? Refer to the 'How To' guide for detailed instructions! 🧙"
        )
    prompt = st.chat_input("Ask away!", disabled=st.session_state.disable_chatbot)
    if prompt:
        # prompt_ai_ready = prompt_message_ai_benchmarking_buddy_latency(
        #     st.session_state["results"], prompt
        # )
        prompt_ai_ready = ""
        st.session_state.messages.append({"role": "user", "content": prompt_ai_ready})
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with respond_conatiner:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(
                    f"<div style='padding: 10px; border-radius: 5px;'>{prompt}</div>",
                    unsafe_allow_html=True,
                )
            # Generate AI response (asynchronously)
            with st.chat_message("assistant", avatar="🤖"):
                stream = st.session_state.azure_openai_manager.openai_client.chat.completions.create(
                    model=st.session_state.azure_openai_manager.chat_model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (SYSTEM_MESSAGE_LATENCY),
                        }
                    ]
                    + [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages
                    ],
                    temperature=st.session_state["settings_buddy"]["temperature"],
                    max_tokens=st.session_state["settings_buddy"]["max_tokens"],
                    presence_penalty=st.session_state["settings_buddy"][
                        "presence_penalty"
                    ],
                    frequency_penalty=st.session_state["settings_buddy"][
                        "frequency_penalty"
                    ],
                    seed=555,
                    stream=True,
                )
                ai_response = st.write_stream(stream)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": ai_response}
                )

async def generate_ai_response(user_prompt: str, system_prompt: str, image_paths: List[str], stream=False, response_format = 'json_object') -> dict:
    try:
        logger.info("Generating AI response...")
        logger.info(f"User Prompt: {user_prompt}")
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"Image Paths: {image_paths}")
        logger.info(f"Stream: {stream}")

        response = await st.session_state['azure_openai_client_4o'].generate_chat_response(
            query=user_prompt, 
            system_message_content=system_prompt, 
            image_paths=image_paths,
            conversation_history=[],
            stream=stream,
            response_format=response_format,
            max_tokens=3000
        )

        logger.info("AI response generated successfully.")
        return response

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return {}

def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    #initialize_session_state(session_vars, initial_values)
    if "azure_openai_client_4o" not in st.session_state:
        st.session_state.azure_openai_client_4o = AzureOpenAIManager(completion_model_name='AZURE_OPENAI_CHAT_DEPLOYMENT_ID')
    configure_sidebar()
    # Create containers for displaying benchmark results
    results_container = st.container(border=True)
    uploaded_files = st.session_state.get("uploaded_files", [])

     # Custom CSS for centering and styling the button with a futuristic AI theme
    st.sidebar.markdown("""
        <style>
        .centered-button-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-top: 10px; /* Adjust the margin as needed */
            width: 100%; /* Ensure the container spans the full width */
        }
        .stButton button {
            background-color: #1E90FF; /* DodgerBlue background */
            border: none; /* Remove borders */
            color: white; /* White text */
            padding: 15px 32px; /* Some padding */
            text-align: center; /* Centered text */
            text-decoration: none; /* Remove underline */
            display: inline-block; /* Make the container inline-block */
            font-size: 18px; /* Increase font size */
            margin: 4px 2px; /* Some margin */
            cursor: pointer; /* Pointer/hand icon */
            border-radius: 12px; /* Rounded corners */
            transition: background-color 0.4s, color 0.4s, border 0.4s; /* Smooth transition effects */
            box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19); /* Add shadow */
        }
        .stButton button:hover {
            background-color: #104E8B; /* Darker blue background on hover */
            color: #00FFFF; /* Cyan text on hover */
            border: 2px solid #104E8B; /* Darker blue border on hover */
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Center the button using a container with the custom CSS class
    st.sidebar.markdown('<div class="centered-button-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.sidebar.columns(3)
    submit_to_ai = col2.button("Submit", key="submit_to_ai", help="Click to submit the uploaded documents for AI analysis.")
    st.markdown('</div>', unsafe_allow_html=True)

    if submit_to_ai and uploaded_files:
        with results_container:
            with st.spinner("Processing files... 🤖"):
                downloaded_folder = process_uploaded_files(uploaded_files)
                if downloaded_folder:
                    extensions = ['png']
                    pa_files_images = find_all_files(downloaded_folder, extensions)

                    # Create a placeholder for the message
                    message_placeholder = st.empty()
                    message_placeholder.markdown("Summarizing Key clinical information and attachments... 📄✨")

                    # Generate AI response
                    api_response_gpt4o = asyncio.run(generate_ai_response(USER_PROMPT_NER, 
                                                                          SYSTEM_PROMPT_NER, 
                                                                          pa_files_images))

                    # Clear the message
                    message_placeholder.empty()
                    
                    if api_response_gpt4o:         
                        SYSTEM_PROMPT_query_expansion = create_prompt_query_expansion(api_response_gpt4o['response']['Clinical Information'])
                        api_response_search = asyncio.run(generate_ai_response(SYSTEM_PROMPT_query_expansion, 
                                                                              SYSTEM_PROMPT_NER, 
                                                                              pa_files_images))

                        # Create a placeholder for the search message
                        search_message_placeholder = st.empty()
                        search_message_placeholder.markdown("Making a Decision... 🔍")
                         # Locate the policy
                        policy_location = locate_policy(api_response_search)
                        policy_text = get_policy_text_from_blob(policy_location)
                        # Clear the search message
                        search_message_placeholder.empty()

                    # if policy_text:
                        
                    #     USER_PROMPT_pa = create_prompt_pa(api_response_gpt4o['response']['Clinical Information'],
                    #                                               policy_text)
                    #     search_message_placeholder_2 = st.empty()
                    #     search_message_placeholder_2.markdown("Making a Decision... 🔍")
                    #     api_response_final = asyncio.run(generate_ai_response(USER_PROMPT_pa, 
                    #                                                           SYSTEM_PROMPT_PRIOR_AUTH, 
                    #                                                           pa_files_images,
                    #                                                           response_format='text'))
                    #     search_message_placeholder_2.empty()
                    with results_container:
                        # Display the response in a tabbed format
                        response = api_response_gpt4o['response']
                        tabs = st.tabs(["Patient Information", "Provider Information", "Clinical Information", "Policy", "Determination"])

                        with tabs[0]:
                            st.header("Patient Information")
                            st.write(response['Patient Information'])

                        with tabs[1]:
                            st.header("Physician Information")
                            st.write(response['Physician Information'])

                        with tabs[2]:
                            st.header("Clinical Information")
                            st.write(response['Clinical Information'])

                        with tabs[3]:
                            st.header("Policy Information")
                            if policy_text:
                                st.markdown(f"**Policy Text (first 2000 characters)**:\n\n```markdown\n{policy_text[:2000]}\n```")
                            st.markdown(f"**Policy Location**: {policy_location}")
                        with tabs[4]:
                            st.header("Determination")
                            st.markdown(DETERMINATION)
                else:
                    st.write("Failed to process files.")
    else:
        st.info("Please upload files to analyze.")
        
    st.sidebar.write(
        """
        <div style="text-align:center; font-size:30px; margin-top:10px;">
            ...
        </div>
        <div style="text-align:center; margin-top:20px;">
            <a href="https://github.com/pablosalvador10" target="_blank" style="text-decoration:none; margin: 0 10px;">
                <img src="https://img.icons8.com/fluent/48/000000/github.png" alt="GitHub" style="width:40px; height:40px;">
            </a>
            <a href="https://www.linkedin.com/in/pablosalvadorlopez/?locale=en_US" target="_blank" style="text-decoration:none; margin: 0 10px;">
                <img src="https://img.icons8.com/fluent/48/000000/linkedin.png" alt="LinkedIn" style="width:40px; height:40px;">
            </a>
            <a href="#" target="_blank" style="text-decoration:none; margin: 0 10px;">
                <img src="https://img.icons8.com/?size=100&id=23438&format=png&color=000000" alt="Blog" style="width:40px; height:40px;">
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    

    st.write(
        """
        <div style="text-align:center; font-size:30px; margin-top:10px;">
            ...
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")
    if 'disable_chatbot' not in st.session_state:
        st.session_state.disable_chatbot = True
    initialize_chatbot()

    if st.session_state.ai_response:
        pass

   

if __name__ == "__main__":
    main()