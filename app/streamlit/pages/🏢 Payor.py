# Load environment variables
import dotenv
import streamlit as st
import asyncio
import uuid
from src.aoai.aoai_helper import AzureOpenAIManager
from app.components.benchmarkbuddy import 
from typing import List, Union
from utils.ml_logging import get_logger
from pathlib import Path
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
import os
from src.pipeline.paprocessing.run import PAProcessingPipeline
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager  # Ensure correct import paths

# Set up logger
logger = get_logger()

# Load environment variables if not already loaded
dotenv.load_dotenv(".env")

cosmosdbManager = CosmosDBMongoCoreManager(
    database_name=os.getenv("AZURE_COSMOS_DATABASE_NAME"),
    collection_name=os.getenv("AZURE_COSMOS_COLLECTION_NAME"),
)

# Define session variables and initial values
session_vars = ["conversation_history", "ai_response", "chat_history", "messages", "azure_openai_client_4o", "uploaded_files", "search_client", "pa_processing", "cosmosdb_manager"]
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
    "azure_openai_client_4o": AzureOpenAIManager(completion_model_name=os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT_ID')),
    "uploaded_files": [],
    "search_client": SearchClient(
        endpoint=os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT"),
        index_name=os.getenv("AZURE_AI_SEARCH_INDEX_NAME"),
        credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")),
    ),
    "pa_processing": PAProcessingPipeline(),
    "cosmosdb_manager": cosmosdbManager
}

for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = initial_values.get(var, None)

for var in session_vars:
    if var not in st.session_state:
        st.session_state[var] = initial_values.get(var, None)

st.set_page_config(
    page_title="SmartPA",
    page_icon="✨",
)    

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
    if "azure_openai_client_4o" not in st.session_state:
        st.session_state.azure_openai_client_4o = AzureOpenAIManager(completion_model_name='AZURE_OPENAI_CHAT_DEPLOYMENT_ID')
    if "pa_processing" not in st.session_state:
        st.session_state.pa_processing = PAProcessingPipeline()

    configure_sidebar()
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
            st.session_state["pa_processing"].run_pipeline(uploaded_files)
            last_key = next(reversed(st.session_state["pa_processing"].results.keys()))
            query = {"caseId": last_key}
            document = cosmosdbManager.read_document(query)
            if document:
                # Create tabs for different sections
                tab1, tab2, tab3, tab4 = st.tabs(["Clinical Information", "Final Determination", "Policy Location", "Raw Uploaded Files"])

                with tab1:
                    st.header("Clinical Information")
                    st.markdown(f"**Clinical Information:** {document.get('Clinical Information', 'N/A')}")
                
                with tab2:
                    st.header("Final Determination")
                    st.markdown(f"<div style='font-size: 18px; color: #1F77B4;'>{document.get('final_determination', 'N/A')}</div>", unsafe_allow_html=True)
                
                with tab3:
                    st.header("Policy Location")
                    st.markdown(f"**Policy Location:** {document.get('policy_location', 'N/A')}")
                
                with tab4:
                    st.header("Raw Uploaded Files")
                    raw_files = document.get('raw_uploaded_files', [])
                    if raw_files:
                        for file in raw_files:
                            st.markdown(f"- {file}")
                    else:
                        st.markdown("No raw uploaded files found.") 
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