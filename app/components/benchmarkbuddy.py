import streamlit as st

from src.app.utils.managers import create_azure_openai_manager


def configure_benchmarkbudyy_model_settings(conf) -> dict:
    """
    Configure AOAI model settings and return the values from each input.

    :return: A dictionary containing the settings values.
    """
    with conf:
        # Ensure 'settings' exists in 'session_state'
        if "settings_buddy" not in st.session_state:
            st.session_state["settings_buddy"] = {}

        st.session_state["settings_buddy"]["temperature"] = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1,
            help="Think of 'Temperature' as the chatbot's creativity control. A higher value makes the chatbot more adventurous, giving you more varied and surprising responses.",
        )
        st.session_state["settings_buddy"]["top_p"] = st.slider(
            "Top P",
            min_value=0.0,
            max_value=1.0,
            value=1.0,
            step=0.01,
            help="The 'Top P' setting helps fine-tune how the chatbot picks its words. Lowering this makes the chatbot's choices more predictable and focused, while a higher setting encourages diversity in responses.",
        )

        st.session_state["settings_buddy"]["max_tokens"] = st.slider(
            "Max Generation Tokens (Input)",
            min_value=100,
            max_value=3000,
            value=1000,
            help="This slider controls how much the chatbot talks. Slide to the right for longer stories or explanations, and to the left for shorter, more concise answers.",
        )

        st.session_state["settings_buddy"]["presence_penalty"] = st.slider(
            "Presence Penalty",
            min_value=-2.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
            help="Use 'Presence Penalty' to manage repetition. Increase it to make the chatbot avoid repeating itself, making each response fresh and unique.",
        )

        st.session_state["settings_buddy"]["frequency_penalty"] = st.slider(
            "Frequency Penalty",
            min_value=-2.0,
            max_value=2.0,
            value=0.0,
            step=0.1,
            help="The 'Frequency Penalty' discourages the chatbot from using the same words too often. A higher penalty encourages a richer vocabulary in responses.",
        )

    return st.session_state["settings_buddy"]


def update_chatbot_configuration():
    """
    Update the chatbot configuration based on the selected deployment.
    """
    if "deployments" in st.session_state and st.session_state.deployments:
        deployment_names = list(st.session_state.deployments.keys())
        selected_deployment_name = st.radio(
            label="Select a deployment to use:",
            options=deployment_names,
            label_visibility="visible",
        )

        if st.button("Update Chatbot Configuration"):
            selected_deployment = st.session_state.deployments[selected_deployment_name]
            st.session_state["AZURE_OPENAI_KEY_CHATBOT"] = selected_deployment["key"]
            st.session_state["AZURE_OPENAI_API_ENDPOINT_CHATBOT"] = selected_deployment[
                "endpoint"
            ]
            st.session_state["AZURE_OPENAI_API_VERSION_CHATBOT"] = selected_deployment[
                "version"
            ]
            st.session_state[
                "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID_CHATBOT"
            ] = selected_deployment_name
            st.success(
                f"Chatbot configuration updated with deployment: {selected_deployment_name}"
            )
    else:
        st.info(
            "😔 No deployments available. Head over to the Deployment Center to add your first deployment."
        )


def init_brain_chatbot(error_client_buddy: st.container) -> None:
    try:
        st.session_state["azure_openai_manager"] = create_azure_openai_manager(
            api_key=st.session_state["AZURE_OPENAI_KEY_CHATBOT"],
            azure_endpoint=st.session_state["AZURE_OPENAI_API_ENDPOINT_CHATBOT"],
            api_version=st.session_state["AZURE_OPENAI_API_VERSION_CHATBOT"],
            deployment_id=st.session_state[
                "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID_CHATBOT"
            ],
        )
        stream = (
            st.session_state.azure_openai_manager.openai_client.chat.completions.create(
                model=st.session_state.azure_openai_manager.chat_model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "Test: Verify setup.",
                    }
                ]
                + [{"role": "user", "content": "test"}],
                max_tokens=2,
                seed=555,
                stream=True,
            )
        )
        st.toast("BenchBuddy 🤖 successfully configured.")
        error_client_buddy.empty()
        st.session_state["disable_chatbot"] = False
    except Exception as e:
        st.warning(
            f"An issue occurred while initializing the Azure OpenAI manager. {e} Please try again. If the issue persists, verify your configuration."
        )


def configure_chatbot() -> None:
    """
    Configure the chatbot capabilities within the Streamlit application.

    This function ensures that the necessary configurations for the chatbot are available in the session state.
    If not, it provides an interface for the user to configure and activate the chatbot.
    """
    error_client_buddy = st.empty()

    # List of required configuration keys
    required_keys = [
        "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID_CHATBOT",
        "AZURE_OPENAI_KEY_CHATBOT",
        "AZURE_OPENAI_API_ENDPOINT_CHATBOT",
        "AZURE_OPENAI_API_VERSION_CHATBOT",
    ]

    # Check if all required keys are present in the session state
    all_keys_exist = all(key in st.session_state for key in required_keys)

    if (
        not all_keys_exist
        or "azure_openai_manager" not in st.session_state
        or not st.session_state.get("azure_openai_manager")
    ):
        error_client_buddy.error(
            "Chatbot capabilities are currently disabled. To activate and fully utilize BenchBuddy knowledge, please configure the AOAI model."
        )

    brain, conf = st.tabs(
        ["🧠 Configure BenchBuddy's Brain", "🔧 Update Chatbot Configuration"]
    )
    with brain:
        st.write(
            "Add the AOAI-model to empower Buddy with advanced cognitive capabilities."
        )

        tabs_1_buddy, tabs_2_buddy = st.tabs(
            ["🔍 Select Deployment", "➕ Add Deployment"]
        )

        with tabs_1_buddy:
            if "deployments" in st.session_state and st.session_state.deployments:
                deployment_names = list(st.session_state.deployments.keys())
                selected_deployment_name = st.radio(
                    label="Select a deployment to use:",
                    options=deployment_names,
                    label_visibility="visible",
                )

                submitted_buddy = st.button(
                    "Add/Update Deployment", use_container_width=True
                )

                if submitted_buddy:
                    selected_deployment = st.session_state.deployments[
                        selected_deployment_name
                    ]
                    st.session_state["AZURE_OPENAI_KEY_CHATBOT"] = selected_deployment[
                        "key"
                    ]
                    st.session_state[
                        "AZURE_OPENAI_API_ENDPOINT_CHATBOT"
                    ] = selected_deployment["endpoint"]
                    st.session_state[
                        "AZURE_OPENAI_API_VERSION_CHATBOT"
                    ] = selected_deployment["version"]
                    st.session_state[
                        "AZURE_AOAI_CHAT_MODEL_NAME_DEPLOYMENT_ID_CHATBOT"
                    ] = selected_deployment_name
                    init_brain_chatbot(error_client_buddy)

            else:
                st.info(
                    "😔 No deployments available. Head over to the Deployment Center to add your first deployment."
                )

        with tabs_2_buddy:
            with st.form("add_deployment_chatbot"):
                for key in required_keys:
                    placeholder_text = _get_placeholder_text(key)
                    input_type = "password" if "KEY" in key else "default"
                    st.session_state[key] = st.text_input(
                        key.split("_")[-1]
                        .replace("CHATBOT", "")
                        .title()
                        .replace("_", " "),
                        help=f"Enter your {key.split('_')[-1].replace('CHATBOT', '').replace('_', ' ').title()}.",
                        type=input_type,
                        placeholder=placeholder_text,
                    )
                submitted_buddy = st.form_submit_button("Add Deployment")

            if submitted_buddy:
                init_brain_chatbot(error_client_buddy)

    configure_benchmarkbudyy_model_settings(conf)

    if st.session_state["azure_openai_manager"]:
        st.markdown(
            f"""Buddy is now responsive, thanks to the deployment: `{st.session_state["azure_openai_manager"].chat_model_name}`."""
        )


def _get_placeholder_text(key: str) -> str:
    """
    Get placeholder text based on the configuration key.

    :param key: The configuration key.
    :return: Placeholder text.
    """
    if "KEY" in key:
        return "e.g., sk-ab*****.."
    elif "DEPLOYMENT_ID" in key:
        return "e.g., chat-gpt-1234abcd"
    elif "ENDPOINT" in key:
        return "e.g., https://api.openai.com/v1"
    elif "VERSION" in key:
        return "e.g., 2024-02-15-preview"
    return ""
