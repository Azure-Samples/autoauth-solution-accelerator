import asyncio
import os
import tempfile
from typing import List

import dotenv
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from src.aoai.aoai_helper import AzureOpenAIManager
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.entraid.generate_id import generate_unique_id
from src.pipeline.paprocessing.run import PAProcessingPipeline
from utils.ml_logging import get_logger

logger = get_logger()

dotenv.load_dotenv(".env", override=True)

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


def configure_sidebar(results_container):
    with st.sidebar:
        st.markdown("")

        st.markdown(
            """
            ## 👩‍⚕️ Welcome to AutoAuth
        
            AutoAuth is an AI-powered tool designed to streamline the Prior Authorization (PA) process.
        
            ### How It Works:
            1. **Upload Your PA Case**: Attach all relevant files, including clinical notes, PDFs, images, and reports.
            2. **Submit for Analysis**: Click 'Submit' and let our AI handle the rest. You'll receive a comprehensive clinical determination. 🤖
        
            ### Need Assistance?
            Feel free to reach out to **AutoAuth Chat** for any questions or further assistance. 🗨️

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


SYSTEM_MESSAGE_LATENCY = """You are a clinical assistant specializing in the prior 
                        authorization process. Your goal is to assist with any questions related to the provision, 
                        evaluation, and determination of prior authorization requests."""


def initialize_chatbot(case_id=None, document=None) -> None:
    st.markdown(
        "<h4 style='text-align: center;'>AutoAuth Chat 🤖</h4>", unsafe_allow_html=True
    )

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    if case_id and st.session_state.get("current_case_id") != case_id:
        st.session_state["chat_history"] = []
        st.session_state["messages"] = []
        st.session_state["current_case_id"] = case_id

        plan_info = document.get("treatment_request", {})
        final_determination = document.get("final_determination", "N/A")
        attachments_info = document.get("raw_uploaded_files", [])
        policy_text = document.get("policy_text", [])

        summary = f"""
        Final Determination: {final_determination}

        Patient Information:
            - **Name:** {document.get('physician_name', 'Not provided')}
            - **Specialty:** {document.get('specialty', 'Not provided')}
            - **Contact:**
            - **Office Phone:** {document.get('physician_contact', {}).get('office_phone', 'Not provided')}
            - **Fax:** {document.get('physician_contact', {}).get('fax', 'Not provided')}
            - **Office Address:** {document.get('physician_contact', {}).get('office_address', 'Not provided')}

        Physician Information:
            - **Name:** {document.get('physician_name', 'Not provided')}
            - **Specialty:** {document.get('specialty', 'Not provided')}
            - **Contact:**
            - **Office Phone:** {document.get('physician_contact', {}).get('office_phone', 'Not provided')}
            - **Fax:** {document.get('physician_contact', {}).get('fax', 'Not provided')}
            - **Office Address:** {document.get('physician_contact', {}).get('office_address', 'Not provided')}

        Clinical Information:
            - **Diagnosis:** {document.get('diagnosis', 'Not provided')}
            - **ICD-10 code:** {document.get('icd_10_code', 'Not provided')}
            - **Detailed History of Prior Treatments and Results:** {document.get('prior_treatments_and_results', 'Not provided')}
            - **Specific drugs already taken by patient and if the patient failed these prior treatments:** {document.get('specific_drugs_taken_and_failures', 'Not provided')}
            - **Alternative Drugs Required by the Specific PA Form:** {document.get('alternative_drugs_required', 'Not provided')}
            - **Relevant Lab Results or Diagnostic Imaging:** {document.get('relevant_lab_results_or_imaging', 'Not provided')}
            - **Documented Symptom Severity and Impact on Daily Life:** {document.get('symptom_severity_and_impact', 'Not provided')}
            - **Prognosis and Risk if Treatment Is Not Approved:** {document.get('prognosis_and_risk_if_not_approved', 'Not provided')}
            - **Clinical Rationale for Urgency:** {document.get('clinical_rationale_for_urgency', 'Not provided')}
            - **Plan for Treatment or Request for Prior Authorization:**
                - **Name of the Medication or Procedure Being Requested:** {plan_info.get('name_of_medication_or_procedure', 'Not provided')}
                - **Code of the Medication or Procedure:** {plan_info.get('code_of_medication_or_procedure', 'Not provided')}
                - **Dosage:** {plan_info.get('dosage', 'Not provided')}
                - **Duration:** {plan_info.get('duration', 'Not provided')}
                - **Rationale:** {plan_info.get('rationale', 'Not provided')}

        Attachments:
        The following attachments were provided by the user and were considered in the final determination:
        {attachments_info}

        Policy Text:
        The following OCR text of the policy was used to make the final decision:
        {policy_text}
        """

        system_prompt = SYSTEM_MESSAGE_LATENCY + "\n\n" + summary
        st.session_state["messages"].append(
            {"role": "system", "content": system_prompt}
        )

        greeting_message = f"👋 How can I assist you with case ID **{case_id}**? Feel free to ask any questions!"
        st.session_state["messages"].append(
            {"role": "assistant", "content": greeting_message}
        )
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": greeting_message}
        )

    elif not case_id and not st.session_state.get("initialized_default"):
        st.session_state["chat_history"] = []
        st.session_state["messages"] = []
        st.session_state["initialized_default"] = True

        st.session_state["messages"].append(
            {"role": "system", "content": SYSTEM_MESSAGE_LATENCY}
        )

        default_message = "🚀 How can I help you today? I'm here to assist with any questions related to the prior authorization process."
        st.session_state["messages"].append(
            {"role": "assistant", "content": default_message}
        )
        st.session_state["chat_history"].append(
            {"role": "assistant", "content": default_message}
        )

    respond_container = st.container(height=400)
    with respond_container:
        for message in st.session_state["chat_history"]:
            role, content = message["role"], message["content"]
            avatar = "🧑‍💻" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                st.markdown(content, unsafe_allow_html=True)

    prompt = st.chat_input("Type your message here...")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.session_state["chat_history"].append({"role": "user", "content": prompt})

        with respond_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(prompt, unsafe_allow_html=True)

            with st.chat_message("assistant", avatar="🤖"):
                messages = st.session_state["messages"]

                stream = st.session_state.azure_openai_client_4o.openai_client.chat.completions.create(
                    model=st.session_state.azure_openai_client_4o.chat_model_name,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4000,
                    stream=True,
                )
                ai_response = st.write_stream(stream)
                st.session_state["messages"].append(
                    {"role": "assistant", "content": ai_response}
                )
                st.session_state["chat_history"].append(
                    {"role": "assistant", "content": ai_response}
                )


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


async def run_pipeline_with_spinner(uploaded_files, use_o1):
    caseID = generate_unique_id()
    with st.spinner("Processing... Please wait."):
        if use_o1:
            st.toast("Using the o1 model for final determination.", icon="🔥")
        await st.session_state["pa_processing"].run(
            uploaded_files, streamlit=True, caseId=caseID, use_o1=use_o1
        )
    last_key = next(reversed(st.session_state["pa_processing"].results.keys()))
    if "case_ids" not in st.session_state:
        st.session_state["case_ids"] = []
    if last_key not in st.session_state["case_ids"]:
        st.session_state["case_ids"].append(last_key)
    return last_key


def display_case_data(document, results_container):
    with results_container:
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
            st.markdown(f"{final_determination}")

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
                if isinstance(policy_retrieval, list) and all(
                    isinstance(policy, str) for policy in policy_retrieval
                ):
                    for policy in policy_retrieval:
                        st.markdown(f"- {policy}")
                else:
                    st.markdown(f"- {policy_retrieval}")
            if raw_uploaded_files:
                st.markdown("Clinical Docs:")
                for doc in raw_uploaded_files:
                    st.markdown(f"- {doc}")
            else:
                st.markdown("No supporting documents found.")


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
    return f"""
    - **Name:** {document.get('patient_name', 'Not provided')}
    - **Date of Birth:** {document.get('patient_date_of_birth', 'Not provided')}
    - **ID:** {document.get('patient_id', 'Not provided')}
    - **Address:** {document.get('patient_address', 'Not provided')}
    - **Phone Number:** {document.get('patient_phone_number', 'Not provided')}
    """


def format_physician_info(document):
    return f"""
    - **Name:** {document.get('physician_name', 'Not provided')}
    - **Specialty:** {document.get('specialty', 'Not provided')}
    - **Contact:**
      - **Office Phone:** {document.get('physician_contact', {}).get('office_phone', 'Not provided')}
      - **Fax:** {document.get('physician_contact', {}).get('fax', 'Not provided')}
      - **Office Address:** {document.get('physician_contact', {}).get('office_address', 'Not provided')}
    """


def format_clinical_info(document):
    plan_info = document.get("treatment_request", {})
    return f"""
    - **Diagnosis:** {document.get('diagnosis', 'Not provided')}
    - **ICD-10 code:** {document.get('icd_10_code', 'Not provided')}
    - **Detailed History of Prior Treatments and Results:** {document.get('prior_treatments_and_results', 'Not provided')}
    - **Specific drugs already taken by patient and if the patient failed these prior treatments:** {document.get('specific_drugs_taken_and_failures', 'Not provided')}
    - **Alternative Drugs Required by the Specific PA Form:** {document.get('alternative_drugs_required', 'Not provided')}
    - **Relevant Lab Results or Diagnostic Imaging:** {document.get('relevant_lab_results_or_imaging', 'Not provided')}
    - **Documented Symptom Severity and Impact on Daily Life:** {document.get('symptom_severity_and_impact', 'Not provided')}
    - **Prognosis and Risk if Treatment Is Not Approved:** {document.get('prognosis_and_risk_if_not_approved', 'Not provided')}
    - **Clinical Rationale for Urgency:** {document.get('clinical_rationale_for_urgency', 'Not provided')}
    - **Plan for Treatment or Request for Prior Authorization:**
      - **Name of the Medication or Procedure Being Requested:** {plan_info.get('name_of_medication_or_procedure', 'Not provided')}
      - **Code of the Medication or Procedure:** {plan_info.get('code_of_medication_or_procedure', 'Not provided')}
      - **Dosage:** {plan_info.get('dosage', 'Not provided')}
      - **Duration:** {plan_info.get('duration', 'Not provided')}
      - **Rationale:** {plan_info.get('rationale', 'Not provided')}
    """


def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    results_container = st.container(border=True)
    configure_sidebar(results_container)
    uploaded_files = st.session_state.get("uploaded_files", [])
    selected_case_id = None  # Initialize variable to track the selected case ID

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

    # Add a radio button in the sidebar to select the model
    st.sidebar.markdown("#### Select Model")
    model_choice = st.sidebar.radio(
        "Choose the model for final determination:",
        ("4o", "o1"),
        index=0,  # Default selection is "4o"
    )
    use_o1 = model_choice == "o1"

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
        uploaded_file_paths = save_uploaded_files(uploaded_files)
        with results_container:
            selected_case_id = asyncio.run(
                run_pipeline_with_spinner(uploaded_file_paths, use_o1)
            )

    if "case_ids" in st.session_state and st.session_state["case_ids"]:
        st.sidebar.divider()
        case_ids = st.session_state["case_ids"][::-1]  # Reverse to show latest first
        default_index = (
            case_ids.index(selected_case_id) if selected_case_id in case_ids else 0
        )

        if "case_ids" in st.session_state and st.session_state["case_ids"]:
            case_ids = st.session_state["case_ids"][
                ::-1
            ]  # Reverse to show latest first
            default_index = (
                case_ids.index(selected_case_id) if selected_case_id in case_ids else 0
            )

            st.sidebar.markdown("#### Retrieve a Case ID to Review")
            selected_case_id = st.sidebar.selectbox(
                "Select PA case ID",
                case_ids,
                index=default_index,
                help="Select a Case ID from the list to view its details and status.",
            )

    if selected_case_id:
        query = {"caseId": selected_case_id}
        document = st.session_state["cosmosdb_manager"].read_document(query)
        if document:
            display_case_data(document, results_container)

            initialize_chatbot(
                case_id=selected_case_id,
                document=document,
            )
        else:
            with results_container:
                st.warning("Case ID not found.")
            initialize_chatbot()
    else:
        st.info(
            "Let's get started! Please upload your PA form and attached files, and let AI do the job."
        )
        initialize_chatbot()

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


if __name__ == "__main__":
    main()
