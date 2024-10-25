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

    This function generates the main content HTML for the Streamlit app.

    :return: The main content HTML.
    """
    return f"""
    <h1 style="text-align:center;">
        Welcome to Bench4AI 🤖!
        <br>
        <span style="font-style:italic; font-size:0.4em;"> Your ultimate LLM/SLM benchmarking destination </span> 
        <img src="data:image/png;base64,{get_image_base64('./my_utils/images/azure_logo.png')}" alt="RAG logo" style="width:25px;height:25px;">        
        <br>
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

@st.cache_data
def get_markdown_content() -> str:
    """
    Get the markdown content for the app.

    This function generates the markdown content for the Streamlit app, providing information about the app's capabilities and resources.

    :return: The markdown content.
    """
    return """
    Bench4AI features a user-friendly interface that streamlines the today's complex benchmarking process for your preferred MaaS (a.k.a Gpt-4o) and candidates. 
    It allows you to bring your own prompts **(BYOP)** for a personalized benchmarking experience with your data. Gain in-depth performance insights with just a few clicks from an extensive library of statistical quality and performance metrics.
    
    #### 🛠️ Automating the Daily Adventures of the AI Engineer

    - **👩‍💼 Tech Lead**: "Hey squad! Just caught wind that Azure OpenAI dropped a shiny new model. When are we integrating it into our app?"

    - **👩🏾‍ Product Manager**: "Hold your horses! We'll sprint through our benchmarking and circle back... will get back to you! ⏱️"

    - **🧑‍💻 The Team Hero**: "Wait... Why not let Bench4AI take it for a spin and.."

    <div style="text-align: center;">
        <img src="https://media.giphy.com/media/5owckHKAKMoA8/giphy.gif" alt="Speedy AI" style="width: 50%; height: auto;">
        <p></p>
    </div>

    <div style="text-align: center;">
        Oh, and say hi to BenchBuddy 🤖! Your go-to AI pal for all things benchmarking.
    </div>

    #### 🌟 Getting Started

    To kick things off, we recommend watching the above introductory video for a smooth start.. If you have any questions, the 'How-To Guide' in the sidebar offers a comprehensive step-by-step walkthrough.

    - **Navigating the App:** The navigation tool in the top right corner is designed for seamless switching between different sections of the app: 
        - 👋 **Home:** The main page you're currently on.
        - 📊 **PerformanceArena:** Gain in-depth insights into model performance, including throughput and latency analysis.
        - 🔍 **QualityIQ:** Assess the accuracy and reliability of your AI models with detailed quality metrics.
  
    #### 💬 Want to Collaborate or Share Your Feedback?
    - **Join Our Community:** Dive into our [chat group](#) to connect with both experts and enthusiasts alike. Share your thoughts, ask questions, and engage with the community.

    - **Feedback Options:**
        - **For Developers/Coders:** We encourage you to provide feedback directly through GitHub Actions. This method allows for a streamlined process to review and implement your valuable suggestions. For step-by-step, please refer to the 'Feedback' section in the sidebar.
        - **For Everyone:** If you don't have access to GitHub, no worries! Your insights are still incredibly important to us. Please share your thoughts by filling out our [feedback form](#). We're eager to hear from you and make improvements based on your feedback.
    """


@st.cache_data
def get_footer_content() -> str:
    """
    Get the footer content HTML for the app.

    This function generates the footer content HTML for the Streamlit app.

    :return: The footer content HTML.
    """
    return """
    <div style="text-align:center; font-size:30px; margin-top:10px;">
        ...
    </div>
    <div style="text-align:center; margin-top:20px;">
        <a href="https://github.com/pablosalvador10/gbb-ai-upgrade-llm" target="_blank" style="text-decoration:none; margin: 0 10px;">
            <img src="https://img.icons8.com/fluent/48/000000/github.png" alt="GitHub" style="width:40px; height:40px;">
        </a>
        <a href="https://www.linkedin.com/in/pablosalvadorlopez/?locale=en_US" target="_blank" style="text-decoration:none; margin: 0 10px;">
            <img src="https://img.icons8.com/fluent/48/000000/linkedin.png" alt="LinkedIn" style="width:40px; height:40px;">
        </a>
        <!-- TODO: Update this link to the correct URL in the future -->
        <a href="#" target="_blank" style="text-decoration:none; margin: 0 10px;">
            <img src="https://img.icons8.com/?size=100&id=23438&format=png&color=000000" alt="Blog" style="width:40px; height:40px;">
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


def display_deployments() -> None:
    """
    Display and manage existing Azure OpenAI deployments.

    This function renders the existing deployments in the Streamlit sidebar, allowing users to view, update, or remove deployments.
    """
    if "deployments" in st.session_state:
        st.markdown("##### Loaded Deployments")
        if st.session_state.deployments == {}:
            st.sidebar.error(
                "No deployments were found. Please add a deployment in the Deployment Center."
            )
        else:
            for deployment_name, deployment in st.session_state.deployments.items():
                with st.expander(deployment_name):
                    updated_name = st.text_input(
                        "Name", value=deployment_name, key=f"name_{deployment_name}"
                    )
                    updated_key = st.text_input(
                        "Key",
                        value=deployment.get("key", ""),
                        type="password",
                        key=f"key_{deployment_name}",
                    )
                    updated_endpoint = st.text_input(
                        "Endpoint",
                        value=deployment.get("endpoint", ""),
                        key=f"endpoint_{deployment_name}",
                    )
                    updated_version = st.text_input(
                        "Version",
                        value=deployment.get("version", ""),
                        key=f"version_{deployment_name}",
                    )
                    updated_stream = st.radio(
                        "Streaming",
                        (True, False),
                        format_func=lambda x: "Yes" if x else "No",
                        index=0 if deployment.get("stream", False) else 1,
                        key=f"stream_{deployment_name}",
                        help="Select 'Yes' if the model will be tested with output in streaming mode.",
                    )

                    if st.button("Update Deployment", key=f"update_{deployment_name}"):
                        st.session_state.deployments[deployment_name] = {
                            "key": updated_key,
                            "endpoint": updated_endpoint,
                            "version": updated_version,
                            "stream": updated_stream,
                        }
                        st.rerun()

                    if st.button("Remove Deployment", key=f"remove_{deployment_name}"):
                        del st.session_state.deployments[deployment_name]
                        st.rerun()
    else:
        st.sidebar.error(
            "No deployments were found. Please add a deployment in the Deployment Center."
        )


def add_deployment_maas_form() -> None:
    """
    Render the form to add a new model deployment.

    This function provides a form in the Streamlit sidebar to add a new deployment, allowing users to specify deployment details.
    """
    with st.form("add_deployment_maas_form"):
        deployment_name = st.text_input(
            "Deployment ID",
            help="Enter the deployment ID for the model.",
            placeholder="e.g., model-deployment-1234abcd",
        )
        deployment_key = st.text_input(
            "API Key",
            help="Enter your API key.",
            type="password",
            placeholder="e.g., sk-ab*****..",
        )
        deployment_endpoint = st.text_input(
            "API Endpoint",
            help="Enter the API endpoint for the model.",
            placeholder="e.g., https://api.model.com/v1",
        )
        model_family = st.selectbox(
            "Model Family",
            [
                "Phi-3 family of models",
                "Cohere Embed V3 family of models",
                "Cohere Command R family of models",
                "Meta Llama 2 chat family of models",
                "Meta Llama 3 instruct family of models",
                "Mistral-Small",
                "Mistral-Large",
                "Jais family of models",
                "Jamba family of models",
            ],
            help="Select the model family for the deployment.",
        )
        # Streaming mode is fixed to non-streaming and disabled
        streaming_mode = st.radio(
            "Streaming Mode",
            ["Non-Streaming"],
            index=0,
            disabled=True,
            help="Streaming mode is fixed to Non-Streaming and cannot be changed.",
        )
        
        submitted = st.form_submit_button("Add Deployment")

        if submitted:
            if (
                deployment_name
                and deployment_key
                and deployment_endpoint
                and model_family
            ):
                if "deployments" not in st.session_state:
                    st.session_state.deployments = {}
                try:
                    pass
                except Exception as e:
                    st.warning(
                        f"""An issue occurred while initializing the model manager. {e} Please try again. If the issue persists,
                                    verify your configuration."""
                    )
                    return

                if deployment_name not in st.session_state.deployments:
                    st.session_state.deployments[deployment_name] = {
                        "key": deployment_key,
                        "endpoint": deployment_endpoint,
                        "model_family": model_family,
                        "streaming_mode": streaming_mode,
                    }
                    st.toast(f"Deployment '{deployment_name}' added successfully.")
                    st.rerun()
                else:
                    st.error(
                        f"A deployment with the name '{deployment_name}' already exists."
                    )


def create_benchmark_center() -> None:
    """
    Creates a benchmark center UI component in a Streamlit application.
    This component allows users to add their MaaS Deployment for benchmarking
    against different model families.

    The function dynamically generates UI elements based on the user's selection
    of model family from a dropdown menu. Currently, it supports the "AOAI" model
    family and provides a placeholder for future expansion to other model families.
    """
    with st.expander("➕ Add Your MaaS Deployment", expanded=False):
        operation = st.selectbox(
            "Choose Model Family:",
            ("AOAI", "Other"),
            index=0,
            help="Select the benchmark you want to perform to evaluate AI model performance.",
            placeholder="Select a Benchmark",
        )
        if operation == "AOAI":
            add_deployment_aoai_form()
        else:
            add_deployment_maas_form()


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

    with st.sidebar:
        st.markdown("## 🤖 Deployment Center ")
        if st.session_state.deployments == {}:
            load_default_deployment()
        create_benchmark_center()
        display_deployments()

    st.sidebar.divider()

    display_support_center()

    st.write(get_main_content(), unsafe_allow_html=True)
    st.markdown(get_markdown_content(), unsafe_allow_html=True)
    st.write(get_footer_content(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
