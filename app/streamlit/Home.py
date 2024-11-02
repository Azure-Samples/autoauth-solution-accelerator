"""
Home.py serves as the foundational script for constructing the home page of a Streamlit application. This application is specifically designed for users to efficiently manage their Azure OpenAI deployments. It provides a user-friendly interface for various operations such as adding new deployment configurations, viewing existing ones, and updating them as needed. The script leverages Streamlit's capabilities to create an interactive web application, making cloud management tasks more accessible and manageable.
"""

import base64
import os
from typing import Any, Dict, Optional

# Load environment variables
import dotenv
import streamlit as st

# Load environment variables if not already loaded
dotenv.load_dotenv(".env")

FROM_EMAIL = "Pablosalvadorlopez@outlook.com"


def get_image_base64(image_path: str) -> str:
    """
    Convert an image file to a base64 string.

    This function reads an image from the specified path and encodes it into a base64 string.

    :param image_path: Path to the image file.
    :return: Base64 encoded string of the image.
    :raises FileNotFoundError: If the image file is not found.
    :raises IOError: If there is an error reading the image file.
    """
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def initialize_session_state(defaults: Dict[str, Any]) -> None:
    """
    Initialize Streamlit session state with default values if not already set.

    This function ensures that the Streamlit session state contains the specified default values if they are not already present.
    :param defaults: Dictionary of default values.
    """
    for var, value in defaults.items():
        if var not in st.session_state:
            st.session_state[var] = value


@st.cache_data
def get_main_content() -> str:
    """
    Get the main content HTML for the app.
    """
    azure_logo_base64 = get_image_base64('./utils/images/azure_logo.png')
    return f"""
    <h1 style="text-align:center;">
        Streamlining Prior Authorization with Azure AI
        <img src="data:image/png;base64,{azure_logo_base64}" alt="Azure Logo" style="width:30px;height:30px;vertical-align:sub;"/>
    </h1>
    """


@st.cache_data()
def create_support_center_content():
    content = {
        "How to Use the Deployment Center": """
            ### 🌟 Getting Started with the Deployment Center

            Adding new deployments allows you to compare performance across multiple MaaS deployments. Follow this step-by-step guide to add and manage your deployments:

            **Step 1: Add Your MaaS Deployment**

            1. Navigate to the `Deployment Center` located at the top of the sidebar.
            2. You will find two sections: `Add your MaaS deployment` and `Loaded deployments`.
                - `Add your MaaS deployment`: Here, you can add a new deployment.
                - `Loaded deployments`: This section displays deployments that are already loaded and ready to use.
            3. To add a new deployment, proceed to the next step.
        
            **Step 2: Add Deployment Details**
            - Fill in the form with the following details:
                - **Deployment ID:** Your chat model deployment ID.
                - **Azure OpenAI Key:** Your Azure OpenAI key (treated as confidential).
                - **API Endpoint:** The endpoint URL for Azure OpenAI.
                - **API Version:** The version of the Azure OpenAI API you're using.
                - **Streaming:** Select 'Yes' if the model will output in streaming mode.
            - Click **Add Deployment** to save your deployment to the session state.

            **Step 3: View and Manage Deployments**
            - Your deployments will be listed under **Loaded Deployments**.
            - Click on a deployment to expand and view its details.
            - You can update any deployment details and click **Update Deployment** to save changes.
            - To remove a deployment, click **Remove Deployment**.
        """,
        "How Deployments are Managed": """
            ### 🌟 Managing Deployments in the Deployment Center
            - Deployments are stored in the Streamlit `session_state`, allowing them to persist across page reloads and be accessible across different pages of the app.
            - This flexibility allows you to easily compare the performance of different deployments and make adjustments as needed.

            **Updating Deployments Across Pages**
            - Any updates made to a deployment from one page are reflected across the entire app, allowing seamless switching between different deployments or updating their configurations without losing context.
        """,
        "How to Collaborate on the Project": """
            ### 🛠️ Resource Links
            - **GitHub Repository:** [Access the GitHub repo](https://github.com/pablosalvador10/gbb-ai-upgrade-llm)
            - **Feedback Form:** [Share your feedback](https://forms.office.com/r/gr8jK9cxuT)

            ### 💬 Want to Collaborate or Share Your Feedback?
            - **Join Our Community:** Connect with experts and enthusiasts in our [community forums](https://forms.office.com/r/qryYbe23T0).
            - **Provide Feedback:** Use our [feedback form](https://forms.office.com/r/gr8jK9cxuT) or [GitHub Issues](https://github.com/pablosalvador10/gbb-ai-upgrade-llm/issues) to share your thoughts and suggestions.
        """,
        "How to Navigate Through the App": """
            ### 🌐 Navigating the App
            - **Home:** This is the main page you're currently on.
            - **Performance Insights:** Gain in-depth insights into model performance, including throughput and latency analysis.
            - **Quality Metrics:** Assess the accuracy and reliability of your AI models with detailed quality metrics.
        """,
        "Feedback": """
            🐞 **Encountered a bug?** Or have a **feature request**? We're all ears!

            Your feedback is crucial in helping us make our service better. If you've stumbled upon an issue or have an idea to enhance our platform, don't hesitate to let us know.

            📝 **Here's how you can help:**
            - Click on the link below to open a new issue on our GitHub repository.
            - Provide a detailed description of the bug or the feature you envision. The more details, the better!
            - Submit your issue. We'll review it as part of our ongoing effort to improve.

            [🔗 Open an Issue on GitHub](https://github.com/pablosalvador10/gbb-ai-upgrade-llm/issues)

            Don't worry if you can't access GitHub! We'd still love to hear your ideas or suggestions for improvements. Just click [here](https://forms.office.com/r/gr8jK9cxuT) to fill out our form. 

            🙏 **Thank you for contributing!** Your insights are invaluable to us.
        """,
    }
    return content


def display_support_center():
    st.sidebar.markdown("## 🛠️ Support Center")
    tab1, tab2 = st.sidebar.tabs(["📘 How-To Guide", "🌟 Feedback!"])
    content = create_support_center_content()

    with tab1:
        for title, markdown_content in content.items():
            if title != "Feedback":
                with st.expander(title):
                    st.markdown(markdown_content)

    with tab2:
        st.markdown(content["Feedback"])

# #### 🚀 Ready to Dive In?

    # <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 10px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.15); width: 80%; margin: auto;">
    #     <iframe src="https://www.loom.com/share/2988afbc761c4348b5299ed55895f128?sid=f7369149-4ab2-4204-8580-0bbdc6a38616" 
    #     frameborder="0" 
    #     webkitallowfullscreen 
    #     mozallowfullscreen 
    #     allowfullscreen 
    #     style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></iframe>
    # </div>

@st.cache_data()
def get_markdown_content() -> str:
    """
    Get the markdown content for the app.
    """

    workflow = get_image_base64('./utils/images/prior_auth.png')
    return f"""
    Prior Authorization (PA) is a process in healthcare where providers must seek approval from payors (insurance companies) before delivering specific treatments or medications. While essential for cost control and care management, the process has become inefficient, creating substantial delays, administrative overheads, and negative outcomes for all stakeholders—providers, payors, and patients.
    
    <br>
    <img src="data:image/png;base64,{workflow}" alt="Prior Authorization Flow" style="display: block; margin-left: auto; margin-right: auto; width: 100%;"/>
    <br>

    ### 🔍 Identifying Challenges and Leveraging Opportunities

    Let's uncover the daily pain points faced by providers and payors, and understand the new landscape for Prior Authorization (PA) with the upcoming 2026 regulations.

    <details>
    <summary>📊 Understanding the Burden for Payors and Providers</summary>
    <br>

    #### ⏳ Time and Cost Implications for Providers and Payors

    **Providers:**
    - **41 Requests per Week:** Physicians handle an average of 41 PA requests per week, consuming around 13 hours, equivalent to two business days [1].
    - **High Administrative Burden:** 88% of physicians report a high or extremely high administrative burden due to PA processes [1].

    **Payors:**
    - **Manual Processing Costs:** Up to 75% of PA tasks are manual or partially manual, costing around $3.14 per transaction [2].
    - **Automation Benefits:** AI can reduce processing costs by up to 40%, cutting manual tasks and reducing expenses to just pennies per request in high-volume cases [2][3].

    #### 🚨 Impact on Patient Outcomes and Delays

    **Providers:**
    - **Treatment Delays:** 93% of physicians report that prior authorization delays access to necessary care, leading to treatment abandonment in 82% of cases [1].
    - **Mortality Risk:** Even a one-week delay in critical treatments like cancer increases mortality risk by 1.2–3.2% [3].

    **Payors:**
    - **Improved Approval Accuracy:** AI automation reduces errors by up to 75%, ensuring more accurate and consistent approvals [2].
    - **Faster Turnaround Times:** AI-enabled systems reduce PA decision-making from days to just hours, leading to improved member satisfaction and reduced costs [3].

    #### ⚙️ Operational Inefficiencies and Automation Potential

    **Providers:**
    - **Transparency Issues:** Providers often lack real-time insight into PA requirements, resulting in treatment delays. AI integration with EHRs can provide real-time updates, improving transparency and reducing bottlenecks [2].

    **Payors:**
    - **High-Volume Auto-Approvals:** AI-based systems can automatically approve low-risk cases, reducing call volumes by 10–15% and improving operational efficiency [2][3].
    - **Efficiency Gains:** AI automation can save 7–10 minutes per case, compounding savings for payors [3].

    #### 📊 Key Statistics: AI’s Impact on PA

    - 40% cost reduction for payors in high-volume cases using AI automation [3].
    - 15–20% savings in call handle time through AI-driven processes [2].
    - 75% of manual tasks can be automated [2].
    - 88% of physicians report high administrative burdens due to PA [1].
    - 93% of physicians report that PA delays patient care [1].

    #### References

    1. American Medical Association, "Prior Authorization Research Reports" [link](https://www.ama-assn.org/practice-management/prior-authorization/prior-authorization-research-reports)
    2. Sagility Health, "Transformative AI to Revamp Prior Authorizations" [link](https://sagilityhealth.com/news/transformative-ai-to-revamp-prior-authorizations/)
    3. McKinsey, "AI Ushers in Next-Gen Prior Authorization in Healthcare" [link](https://www.mckinsey.com/industries/healthcare/our-insights/ai-ushers-in-next-gen-prior-authorization-in-healthcare)

    </details>

    <details>
    <summary>🏛️ Impact of CMS (Centers for Medicare & Medicaid Services) New Regulations</summary>
    <br>

    **Real-Time Data Exchange:** The new regulations mandate that payors use APIs based on HL7 FHIR standards to facilitate real-time data exchange. This will allow healthcare providers to receive quicker PA decisions—within 72 hours for urgent cases and 7 days for standard requests. Immediate access to PA determinations will dramatically reduce delays, ensuring that patients get the necessary care faster. For AI-driven solutions, this real-time data will enable enhanced decision-making capabilities, streamlining the interaction between payors and providers.

    **Transparency in Decision-Making:** Payors will now be required to provide detailed explanations for PA decisions, including reasons for denial, through the Prior Authorization API. This will foster greater transparency, which has been a longstanding issue in the PA process. For AI solutions, this transparency can be leveraged to improve algorithms that predict authorization outcomes, thereby reducing manual reviews and cutting down on administrative burdens. The transparency also enhances trust between providers and payors, reducing disputes over PA decisions.

    </details>

    <div style="text-align:center; font-size:30px; margin-top:10px;">
            ...
    </div>

    ### 🤖👩‍⚕️ Meet PRISM: Our Solution for Payors 

    **PRISM** – **P**rior **R**equest **I**ntelligent **S**ystem for **M**edical Authorization is a comprehensive solution designed to optimize the Prior Authorization (PA) process for healthcare providers. By leveraging advanced AI and automation, PRISM ensures faster, more accurate PA decisions, reducing administrative burdens and improving patient care.

    Please navigate to the Payor page to explore our solution designed to streamline the Prior Authorization (PA) process. Our goal is to reduce administrative burdens, enhance accuracy, and improve productivity by leveraging advanced AI and automation. By implementing PRISM, healthcare providers can process more cases efficiently, reduce bottlenecks, and lower expenses.


    """

@st.cache_data()
def get_footer_content() -> str:
    """
    Get the footer content HTML for the app.
    """
    return """
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
    """


def load_default_deployment(
    name: Optional[str] = None,
    key: Optional[str] = None,
    endpoint: Optional[str] = None,
    version: Optional[str] = None,
) -> None:
    """
    Load default deployment settings, optionally from provided parameters.

    Ensures that a deployment with the same name does not already exist.

    :param name: (Optional) Name of the deployment.
    :param key: (Optional) Azure OpenAI key.
    :param endpoint: (Optional) API endpoint for Azure OpenAI.
    :param version: (Optional) API version for Azure OpenAI.
    :raises ValueError: If required deployment settings are missing.
    """
    # Ensure deployments is a dictionary
    if "deployments" not in st.session_state or not isinstance(
        st.session_state.deployments, dict
    ):
        st.session_state.deployments = {}

    # Check if the deployment name already exists
    deployment_name = (
        name if name else os.getenv("AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID")
    )
    if deployment_name in st.session_state.deployments:
        return  # Exit the function if deployment already exists

    default_deployment = {
        "name": deployment_name,
        "key": key if key else os.getenv("AZURE_OPENAI_KEY"),
        "endpoint": endpoint if endpoint else os.getenv("AZURE_OPENAI_API_ENDPOINT"),
        "version": version if version else os.getenv("AZURE_OPENAI_API_VERSION"),
        "stream": False,
    }

    if all(
        value is not None for value in default_deployment.values() if value != False
    ):
        st.session_state.deployments[default_deployment["name"]] = default_deployment



def add_deployment_aoai_form() -> None:
    """
    Render the form to add a new Azure OpenAI deployment.

    This function provides a form in the Streamlit sidebar to add a new deployment, allowing users to specify deployment details.
    """
    with st.form("add_deployment_aoai_form"):
        deployment_name = st.text_input(
            "Deployment id",
            help="Enter the deployment ID for Azure OpenAI.",
            placeholder="e.g., chat-gpt-1234abcd",
        )
        deployment_key = st.text_input(
            "Azure OpenAI Key",
            help="Enter your Azure OpenAI key.",
            type="password",
            placeholder="e.g., sk-ab*****..",
        )
        deployment_endpoint = st.text_input(
            "API Endpoint",
            help="Enter the API endpoint for Azure OpenAI.",
            placeholder="e.g., https://api.openai.com/v1",
        )
        deployment_version = st.text_input(
            "API Version",
            help="Enter the API version for Azure OpenAI.",
            placeholder="e.g., 2024-02-15-preview",
        )
        is_streaming = st.radio(
            "Streaming",
            (True, False),
            index=1,
            format_func=lambda x: "Yes" if x else "No",
            help="Select 'Yes' if the model will be tested with output in streaming mode.",
        )
        submitted = st.form_submit_button("Add Deployment")

        if submitted:
            if (
                deployment_name
                and deployment_key
                and deployment_endpoint
                and deployment_version
            ):
                if "deployments" not in st.session_state:
                    st.session_state.deployments = {}

                try:
                   pass
                except Exception as e:
                    st.warning(
                        f"""An issue occurred while initializing the Azure OpenAI manager. {e} Please try again. If the issue persists,
                                    verify your configuration."""
                    )
                    return

                if deployment_name not in st.session_state.deployments:
                    st.session_state.deployments[deployment_name] = {
                        "key": deployment_key,
                        "endpoint": deployment_endpoint,
                        "version": deployment_version,
                        "stream": is_streaming,
                    }
                    st.toast(f"Deployment '{deployment_name}' added successfully.")
                    st.rerun()
                else:
                    st.error(
                        f"A deployment with the name '{deployment_name}' already exists."
                    )


def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    st.set_page_config(
        page_title="Home",
        page_icon="👋",
    )

    env_vars = {
        "AZURE_OPENAI_KEY": "",
        "AZURE_OPENAI_API_ENDPOINT": "",
        "AZURE_OPENAI_API_VERSION": "",
        "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID": "",
        "deployments": {},
    }
    initialize_session_state(env_vars)

    display_support_center()

    st.write(get_main_content(), unsafe_allow_html=True)
    st.markdown(get_markdown_content(), unsafe_allow_html=True)
    st.write(get_footer_content(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
