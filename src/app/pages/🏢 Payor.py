# Load environment variables
import dotenv
import streamlit as st
from src.app.utils.benchmarkbuddy import configure_chatbot

# Load environment variables if not already loaded
dotenv.load_dotenv(".env")

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
                                        
        # Custom CSS for centering and styling the button with a futuristic AI theme
        st.markdown("""
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
        st.markdown('<div class="centered-button-container">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        submit_to_ai = col2.button("Submit", key="submit_to_ai", help="Click to submit the uploaded documents for AI analysis.")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if submit_to_ai:
            st.write("Button clicked!")
        
        if submit_to_ai:
            st.write("Button clicked!")
                
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

def initialize_chatbot() -> None:
    """
    Initialize a chatbot interface for user interaction with enhanced features.
    """
    st.markdown(
        "<h4 style='text-align: center;'>BenchBuddy 🤖</h4>",
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
        prompt_ai_ready = prompt_message_ai_benchmarking_buddy_latency(
            st.session_state["results"], prompt
        )
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

def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    #initialize_session_state(session_vars, initial_values)
    configure_sidebar()
    # Create containers for displaying benchmark results
    results_container = st.container()

    st.write(
        """
        <div style="text-align:center; font-size:30px; margin-top:10px;">
            ...
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")
    initialize_chatbot()

    if st.session_state.ai_response:
        pass

   

if __name__ == "__main__":
    main()