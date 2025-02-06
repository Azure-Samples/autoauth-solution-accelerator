import asyncio
import io
import os
import shutil
import tempfile
import zipfile
from typing import List

import dotenv
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

from src.aoai.aoai_helper import AzureOpenAIManager
from src.cosmosdb.cosmosmongodb_helper import CosmosDBMongoCoreManager
from src.entraid.generate_id import generate_unique_id
from src.pipeline.paprocessing.run import PAProcessingPipeline
from src.utils.ml_logging import get_logger

logger = get_logger()

dotenv.load_dotenv(".env", override=True)

# Initialize session state managers
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

# # Initialize PAProcessingPipeline in session state
# if "pa_processing" not in st.session_state:
#     st.session_state["pa_processing"] = PAProcessingPipeline(send_cloud_logs=True)

# Initialize other session variables
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
    page_title="AutoAuth",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)


def cleanup_temp_dir(temp_dir) -> None:
    """
    Cleans up the temporary directory used for processing files.
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.info(f"Cleaned up temporary directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Failed to clean up temporary directory '{temp_dir}': {e}")


def configure_sidebar(results_container):
    with st.sidebar:
        st.markdown("")
        st.markdown(
            """
            ## 👩‍⚕️ Welcome to AutoAuth

            AutoAuth is an AI-powered tool designed to streamline the Prior Authorization (PA) process.

            ### How It Works:
            1. **Upload Your PA Case**: Attach all relevant files, including clinical notes, PDFs, images, and reports.
            2. **Submit for Analysis**: Click **Submit** and let our AI handle the rest. You'll receive a comprehensive clinical determination. 🤖
            """
        )

        with st.expander("⚠️ Disclaimer"):
            st.markdown(
                """
            **Please do not upload personal or sensitive information.** All documents submitted are for analysis purposes only. Ensure all data is anonymized and contains no personally identifiable information (PII).

            For testing, you can download a sample PA case by clicking the button below.

            """
            )

            files_to_zip = [
                "utils/data/cases/003/b/doctor_notes/003_b (note) .pdf",
                "utils/data/cases/003/b/labs/003_b (labs) .pdf",
                "utils/data/cases/003/b/pa_form/003_b (form).pdf",
                "utils/data/cases/003/a/doctor_notes/003_a (note) .pdf",
                "utils/data/cases/003/a/labs/003_a (labs).pdf",
                "utils/data/cases/003/a/pa_form/003_a (form).pdf",
            ]

            existing_files = []
            for file_path in files_to_zip:
                if os.path.exists(file_path):
                    existing_files.append(file_path)
                else:
                    st.warning(f"⚠️ File not found and will be skipped: {file_path}")

            if existing_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for file_name in existing_files:
                        with open(file_name, "rb") as f:
                            zip_file.writestr(os.path.basename(file_name), f.read())

                st.download_button(
                    label="⬇️ Download Sample Files",
                    data=zip_buffer.getvalue(),
                    file_name="sample_files.zip",
                    mime="application/zip",
                    help="Download sample documents to see how AutoAuth works.",
                )
            else:
                st.info("ℹ️ Sample files are not available for download at this time.")

        st.write(
            """
        <div style="text-align:center; font-size:30px; margin-top:10px;">
            ...
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("")

        # File uploader
        uploaded_files = st.file_uploader(
            "Upload PA Case Files",
            type=["png", "jpg", "jpeg", "pdf"],
            accept_multiple_files=True,
            help="Upload documents for AI analysis. If you don't have data available, please download sample files from the Disclaimer section above.",
        )

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

        plan_info = document["ocr_ner_results"]["clinical_info"]["treatment_request"]
        patient_info = document["ocr_ner_results"]["patient_info"]
        physician_info = document["ocr_ner_results"]["physician_info"]
        clinical_info = document["ocr_ner_results"]["clinical_info"]
        final_determination = document.get("pa_determination_results", "N/A")
        attachments_info = document.get("raw_uploaded_files", [])
        # TODO add policy text
        policy_text = document["agenticrag_results"]["policies"]

        summary = f"""
        Final Determination: {final_determination}

        Patient Information:
            - **Name:** {patient_info.get('physician_name', 'Not provided')}
            - **Specialty:** {patient_info.get('specialty', 'Not provided')}
            - **Contact:**
            - **Office Phone:** {patient_info.get('physician_contact', {}).get('office_phone', 'Not provided')}
            - **Fax:** {patient_info.get('physician_contact', {}).get('fax', 'Not provided')}
            - **Office Address:** {patient_info.get('physician_contact', {}).get('office_address', 'Not provided')}

        Physician Information:
            - **Name:** {physician_info.get('physician_name', 'Not provided')}
            - **Specialty:** {physician_info.get('specialty', 'Not provided')}
            - **Contact:**
            - **Office Phone:** {physician_info.get('physician_contact', {}).get('office_phone', 'Not provided')}
            - **Fax:** {physician_info.get('physician_contact', {}).get('fax', 'Not provided')}
            - **Office Address:** {physician_info.get('physician_contact', {}).get('office_address', 'Not provided')}

        Clinical Information:
            - **Diagnosis:** {clinical_info.get('diagnosis', 'Not provided')}
            - **ICD-10 code:** {clinical_info.get('icd_10_code', 'Not provided')}
            - **Detailed History of Prior Treatments and Results:** {clinical_info.get('prior_treatments_and_results', 'Not provided')}
            - **Specific drugs already taken by patient and if the patient failed these prior treatments:** {clinical_info.get('specific_drugs_taken_and_failures', 'Not provided')}
            - **Alternative Drugs Required by the Specific PA Form:** {clinical_info.get('alternative_drugs_required', 'Not provided')}
            - **Relevant Lab Results or Diagnostic Imaging:** {clinical_info.get('relevant_lab_results_or_imaging', 'Not provided')}
            - **Documented Symptom Severity and Impact on Daily Life:** {clinical_info.get('symptom_severity_and_impact', 'Not provided')}
            - **Prognosis and Risk if Treatment Is Not Approved:** {clinical_info.get('prognosis_and_risk_if_not_approved', 'Not provided')}
            - **Clinical Rationale for Urgency:** {clinical_info.get('clinical_rationale_for_urgency', 'Not provided')}
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

        pa_processing = PAProcessingPipeline(send_cloud_logs=True)

        await pa_processing.run(
            uploaded_files, streamlit=True, caseId=caseID, use_o1=use_o1
        )

    last_key = next(iter(pa_processing.results.keys()))

    if "case_ids" not in st.session_state:
        st.session_state["case_ids"] = []

    if last_key not in st.session_state["case_ids"]:
        st.session_state["case_ids"].append(last_key)

    if "pa_processing_results" not in st.session_state:
        st.session_state["pa_processing_results"] = {}

    st.session_state["pa_processing_results"][last_key] = pa_processing.results[
        last_key
    ]

    st.session_state["uploaded_files"] = []

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
            final_determination = document.get("pa_determination_results", "N/A")
            st.markdown(f"{final_determination}")

        with tab2:
            st.header("🩺 Clinical Information")
            data_clinical = format_clinical_info(document.get("ocr_ner_results", {}))
            st.markdown(data_clinical)

        with tab3:
            st.header("👨‍⚕️ Physician Information")
            data_physician = format_physician_info(document.get("ocr_ner_results", {}))
            st.markdown(data_physician)

        with tab4:
            st.header("👤 Patient Information")
            data_patient = format_patient_info(document.get("ocr_ner_results", {}))
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
    return file_paths, temp_dir


def format_patient_info(document):
    document = document.get("patient_info", {})
    return f"""
    - **Name:** {document.get('patient_name', 'Not provided')}
    - **Date of Birth:** {document.get('patient_date_of_birth', 'Not provided')}
    - **ID:** {document.get('patient_id', 'Not provided')}
    - **Address:** {document.get('patient_address', 'Not provided')}
    - **Phone Number:** {document.get('patient_phone_number', 'Not provided')}
    """


def format_physician_info(document):
    document = document.get("physician_info", {})
    return f"""
    - **Name:** {document.get('physician_name', 'Not provided')}
    - **Specialty:** {document.get('specialty', 'Not provided')}
    - **Contact:**
      - **Office Phone:** {document.get('physician_contact', {}).get('office_phone', 'Not provided')}
      - **Fax:** {document.get('physician_contact', {}).get('fax', 'Not provided')}
      - **Office Address:** {document.get('physician_contact', {}).get('office_address', 'Not provided')}
    """


def format_clinical_info(document):
    document = document.get("clinical_info", {})
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

    USE_O1 = True

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

    st.sidebar.markdown("")
    st.sidebar.markdown(
        """💬 **Questions about the policy or AI results?** **AutoAuth Chat** is here to assist you. Try it !"""
    )

    if submit_to_ai and uploaded_files:
        uploaded_file_paths, temp_dir = save_uploaded_files(uploaded_files)
        try:
            with results_container:
                selected_case_id = asyncio.run(
                    run_pipeline_with_spinner(uploaded_file_paths, USE_O1)
                )
        finally:
            cleanup_temp_dir(temp_dir)

    if "case_ids" in st.session_state and st.session_state["case_ids"]:
        st.sidebar.divider()
        case_ids = st.session_state["case_ids"][::-1]  # Reverse to show latest first
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
        if "pa_processing_results" in st.session_state:
            document = st.session_state["pa_processing_results"].get(
                selected_case_id, {}
            )
        else:
            document = {}
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
