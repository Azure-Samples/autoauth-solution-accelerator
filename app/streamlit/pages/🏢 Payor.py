import dotenv
import streamlit as st
import asyncio
import tempfile
from src.aoai.aoai_helper import AzureOpenAIManager
from typing import List
from utils.ml_logging import get_logger
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from src.pipeline.paprocessing.run import PAProcessingPipeline
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager  # Ensure correct import paths

# Set up logger
logger = get_logger()

# Load environment variables if not already loaded
dotenv.load_dotenv(".env", override=True)

# Initialize clients only once and store them in session_state
if "cosmosdb_manager" not in st.session_state:
    st.session_state["cosmosdb_manager"] = CosmosDBMongoCoreManager(
        connection_string=os.getenv("AZURE_COSMOS_CONNECTION_STRING"),
        database_name=os.getenv("AZURE_COSMOS_DB_DATABASE_NAME"),
        collection_name=os.getenv("AZURE_COSMOS_DB_COLLECTION_NAME"),
    )

if "azure_openai_client_4o" not in st.session_state:
    st.session_state["azure_openai_client_4o"] = AzureOpenAIManager(
        completion_model_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
    )

if "search_client" not in st.session_state:
    st.session_state["search_client"] = SearchClient(
        endpoint=os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT"),
        index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
        credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_ADMIN_KEY")),
    )

if "pa_processing" not in st.session_state:
    st.session_state["pa_processing"] = PAProcessingPipeline()

# Define other session variables and initial values
session_vars = [
    "conversation_history",
    "ai_response",
    "chat_history",
    "messages",
    "uploaded_files",
    "disable_chatbot",
]

initial_values = {
    "conversation_history": [],
    "ai_response": "",
    "chat_history": [],
    "disable_chatbot": True,
    "messages": [
        {
            "role": "assistant",
            "content": "Hey, this is your AI assistant. Please look at the AI request submit and let's work together to make your content shine!",
        }
    ],
    "uploaded_files": [],
}

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
            2. **Submit for Analysis**: Click 'Submit' and let our AI handle the rest. You'll receive a comprehensive clinical determination. 🎩

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


SYSTEM_MESSAGE_LATENCY = '''You are a clinical assistant specializing in the prior 
                        authorization process. Your goal is to assist with any questions related to the provision, 
                        evaluation, and determination of prior authorization requests.'''

def initialize_chatbot() -> None:
    st.markdown(
        "<h4 style='text-align: center;'>PriorBuddy 🤖</h4>",
        unsafe_allow_html=True,
    )

    st.session_state.setdefault('chat_history', [])
    st.session_state.setdefault('messages', [])

    if not any(msg.get('role') == 'system' for msg in st.session_state['messages']):
        st.session_state['messages'].insert(0, {'role': 'system', 'content': SYSTEM_MESSAGE_LATENCY})

    respond_container = st.container()

    with respond_container:
        for message in st.session_state.chat_history:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            avatar_style = "🧑‍💻" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar_style):
                st.markdown(f"{content}", unsafe_allow_html=True)

    prompt = st.chat_input("Ask away!")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with respond_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(f"{prompt}", unsafe_allow_html=True)
            # Generate AI response
            with st.chat_message("assistant", avatar="🤖"):
                stream = st.session_state.azure_openai_client_4o.openai_client.chat.completions.create(
                    model=st.session_state.azure_openai_client_4o.chat_model_name,
                    messages=st.session_state.messages,
                    temperature=0,
                    max_tokens=3000,
                    stream=True,
                )
                ai_response = st.write_stream(stream)
                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})



async def generate_ai_response(
    user_prompt: str,
    system_prompt: str,
    image_paths: List[str],
    stream=False,
    response_format="json_object",
) -> dict:
    try:
        logger.info("Generating AI response...")
        logger.info(f"User Prompt: {user_prompt}")
        logger.info(f"System Prompt: {system_prompt}")
        logger.info(f"Image Paths: {image_paths}")
        logger.info(f"Stream: {stream}")

        response = await st.session_state[
            "azure_openai_client_4o"
        ].generate_chat_response(
            query=user_prompt,
            system_message_content=system_prompt,
            image_paths=image_paths,
            conversation_history=[],
            stream=stream,
            response_format=response_format,
            max_tokens=3000,
        )

        logger.info("AI response generated successfully.")
        return response

    except Exception as e:
        logger.error(f"Error generating AI response: {e}")
        return {}


async def run_pipeline_with_spinner(uploaded_files):
    with st.spinner("Processing... Please wait."):
        await st.session_state["pa_processing"].run(uploaded_files, streamlit=True)
    return st.session_state["pa_processing"].conversation_history


def save_uploaded_files(uploaded_files):
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    for uploaded_file in uploaded_files:
        file_path = os.path.join(temp_dir, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        file_paths.append(file_path)
    return file_paths


def format_patient_info(document):
    patient_info = document["Patient Information"]
    return f"""
    - **Name:** {patient_info.get('Patient Name', 'N/A')}
    - **Date of Birth:** {patient_info.get('Patient Date of Birth', 'N/A')}
    - **ID:** {patient_info.get('Patient ID', 'N/A')}
    - **Address:** {patient_info.get('Patient Address', 'N/A')}
    - **Phone Number:** {patient_info.get('Patient Phone Number', 'N/A')}
    """


def format_physician_info(document):
    physician_info = document["Physician Information"]
    return f"""
    - **Name:** {physician_info.get('Physician Name', 'N/A')}
    - **Specialty:** {physician_info.get('Specialty', 'N/A')}
    - **Contact:**
      - **Office Phone:** {physician_info.get('Physician Contact', {}).get('Office Phone', 'N/A')}
      - **Fax:** {physician_info.get('Physician Contact', {}).get('Fax', 'N/A')}
      - **Office Address:** {physician_info.get('Physician Contact', {}).get('Office Address', 'N/A')}
    """


def format_clinical_info(document):
    clinical_info = document["Clinical Information"]
    return f"""
    - **Diagnosis and Medical Justification:** {clinical_info.get('Diagnosis and medical justification (including ICD-10 code)', 'N/A')}
    - **Detailed History of Alternative Treatments and Results:** {clinical_info.get('Detailed history of alternative treatments and results', 'N/A')}
    - **Relevant Lab Results or Diagnostic Imaging:** {clinical_info.get('Relevant lab results or diagnostic imaging', 'N/A')}
    - **Documented Symptom Severity and Impact on Daily Life:** {clinical_info.get('Documented symptom severity and impact on daily life', 'N/A')}
    - **Prognosis and Risk if Treatment is Not Approved:** {clinical_info.get('Prognosis and risk if treatment is not approved', 'N/A')}
    - **Clinical Rationale for Urgency:** {clinical_info.get('Clinical rationale for urgency (if applicable)', 'N/A')}
    - **Plan for Treatment or Request for Prior Authorization:**
      - **Medication or Procedure:** {clinical_info.get('Plan for Treatment or Request for Prior Authorization', {}).get('Medication or Procedure', 'N/A')}
      - **Code:** {clinical_info.get('Plan for Treatment or Request for Prior Authorization', {}).get('Code', 'N/A')}
      - **Dosage:** {clinical_info.get('Plan for Treatment or Request for Prior Authorization', {}).get('Dosage', 'N/A')}
      - **Duration:** {clinical_info.get('Plan for Treatment or Request for Prior Authorization', {}).get('Duration', 'N/A')}
      - **Rationale:** {clinical_info.get('Plan for Treatment or Request for Prior Authorization', {}).get('Rationale', 'N/A')}
    """


def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    configure_sidebar()
    results_container = st.container(border=True)
    uploaded_files = st.session_state.get("uploaded_files", [])

    conversation_history = []

    # Custom CSS for centering and styling the button with a professional look
    st.sidebar.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    # Center the button using a container with the custom CSS class
    st.sidebar.markdown(
        '<div class="centered-button-container">', unsafe_allow_html=True
    )
    col1, col2, col3 = st.sidebar.columns(3)
    submit_to_ai = col2.button(
        "Submit",
        key="submit_to_ai",
        help="Click to submit the uploaded documents for AI analysis.",
    )
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    if submit_to_ai and uploaded_files:
        with results_container:
            uploaded_file_paths = save_uploaded_files(uploaded_files)
            conversation_history = asyncio.run(run_pipeline_with_spinner(uploaded_file_paths))
            st.session_state["conversation_history"].extend(conversation_history)
             # Flatten the conversation history if needed
            if isinstance(conversation_history, list) and len(conversation_history) == 1 and isinstance(conversation_history[0], list):
                conversation_history = conversation_history[0]
            
            # Ensure conversation_history is in the correct format
            if isinstance(conversation_history, list) and all(isinstance(msg, dict) for msg in conversation_history):
                new_messages = [msg for msg in conversation_history if msg not in st.session_state["messages"]]
                st.session_state["conversation_history"].extend(new_messages)
                st.session_state["messages"].extend(new_messages)
                st.session_state["chat_history"].extend(new_messages)
            else:
                st.error("Invalid conversation history format. Expected a list of dictionaries.")
            last_key = next(reversed(st.session_state["pa_processing"].results.keys()))
            query = {"caseId": last_key}
            document = st.session_state["cosmosdb_manager"].read_document(query)

        if document:
            tab1, tab2, tab3, tab4, tab5 = st.tabs(
                [
                    "📋 AI Determination",
                    "🩺 Clinical Information",
                    "👨‍⚕️ Physician Information",
                    "👤 Patient Information",
                    "📑 Supporting Documentation",
                ]
            )

            with tab1:
                st.header("📋 AI Determination")
                final_determination = document.get("final_determination", "N/A")
                st.markdown(f"**Final Determination:** {final_determination}")

            with tab2:
                st.header("🩺 Clinical Information")
                data_clinical = format_clinical_info(document)
                st.markdown(data_clinical)

            with tab3:
                st.header("👨‍⚕️ Physician Information")
                data_physician = format_physician_info(document)
                st.markdown(data_physician)

            with tab4:
                st.header("👤 Patient Information")
                data_patient = format_patient_info(document)
                st.markdown(data_patient)

            with tab5:
                st.header("📑 Supporting Documentation")
                policy_retrieval = document.get("policy_location", [])
                raw_uploaded_files = document.get("raw_uploaded_files", [])
                if policy_retrieval:
                    st.markdown("Policy Leveraged:")
                    for policy in policy_retrieval:
                        st.markdown(f"- {policy}")
                if raw_uploaded_files:
                    st.markdown("Clinical Docs:")
                    for doc in raw_uploaded_files:
                        st.markdown(f"- {doc}")
                else:
                    st.markdown("No supporting documents found.")
    else:
        st.info("Let's get started ! Please upload your PA form and attached files, and let AI do the job.")

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
                    <a href="https://pabloaicorner.hashnode.dev/" target="_blank" style="text-decoration:none; margin: 0 10px;">
                        <img src="https://img.icons8.com/ios-filled/50/000000/blog.png" alt="Blog" style="width:40px; height:40px;">
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
    if "disable_chatbot" not in st.session_state:
        st.session_state.disable_chatbot = True
    initialize_chatbot()


if __name__ == "__main__":
    main()