"""
Home.py serves as the foundational script for constructing the home page of a Streamlit application. This application is specifically designed for users to efficiently manage their Azure OpenAI deployments. It provides a user-friendly interface for various operations such as adding new deployment configurations, viewing existing ones, and updating them as needed. The script leverages Streamlit's capabilities to create an interactive web application, making cloud management tasks more accessible and manageable.
"""

import base64
from typing import Any, Dict

# Load environment variables
import dotenv
import streamlit as st

# Load environment variables if not already loaded
dotenv.load_dotenv(".env")


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
    azure_logo_base64 = get_image_base64("./utils/images/azure_logo.png")
    return f"""
    <h1 style="text-align:center;">
        Streamlining Prior Authorization with Azure AI
        <img src="data:image/png;base64,{azure_logo_base64}" alt="Azure Logo" style="width:30px;height:30px;vertical-align:sub;"/>
    </h1>
    """


@st.cache_data()
def create_support_center_content():
    content = {
        "How to Collaborate on the Project": """
            ### 🛠️ Resource Links
            - **GitHub Repository:** [Access the GitHub repo](https://github.com/pablosalvador10/gbb-ai-hls-factory-prior-auth)
            - **Feedback Form:** [Share your feedback](https://forms.office.com/r/gr8jK9cxuT)

            ### 💬 Want to Collaborate or Share Your Feedback?
            - **Join Our Community:** Connect with experts and enthusiasts in our [community forums](https://forms.office.com/r/qryYbe23T0).
            - **Provide Feedback:** Use our [feedback form](https://forms.office.com/r/gr8jK9cxuT) or [GitHub Issues](https://github.com/pablosalvador10/gbb-ai-hls-factory-prior-auth/issues) to share your thoughts and suggestions.
        """,
        "How to Navigate Through the App": """
            ### 🌐 Navigating AutoAuth
            - **Home:** This is the main page you're currently on.
            - **Payor:** Explore AutoAuth.
            - **Provider:** WIP..AutoAuth for providers will be Available soon. Stay tuned!
        """,
        "Feedback": """
            🐞 **Encountered a bug?** Or have a **feature request**? We're all ears!

            Your feedback is crucial in helping us improve AutoAuth. If you've found an issue or have an idea to enhance our platform, please let us know.

            📝 **Here's how you can help:**
            - Click on the link below to open a new issue on our GitHub repository.
            - Provide a detailed description of the bug or the feature you envision. The more details, the better!
            - Submit your issue. We'll review it as part of our ongoing effort to improve.

            [🔗 Open an Issue on GitHub](https://github.com/pablosalvador10/gbb-ai-hls-factory-prior-auth/issues)

            If you can't access GitHub, we'd still love to hear your ideas or suggestions for improvements. Just click [here](https://forms.office.com/r/gr8jK9cxuT) to fill out our form.

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


@st.cache_data()
def get_markdown_content() -> str:
    """
    Get the markdown content for the app.
    """

    workflow = get_image_base64("./utils/images/prior_auth.png")
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

    ### 🤖👩‍⚕️ Introducing AutoAuth: Streamlining Prior Authorization

    **AutoAuth** is an AI-powered solution designed to optimize the Prior Authorization (PA) process. By leveraging advanced technology, AutoAuth ensures faster and more accurate PA decisions, reducing administrative burdens and enhancing patient care.

    Visit the **Payor** page to explore our tailored solution for payors, aimed at improving efficiency and reducing operational costs.
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


def main() -> None:
    """
    Main function to run the Streamlit app.
    """
    st.set_page_config(
        page_title="Home",
        page_icon="👋",
    )

    display_support_center()

    st.write(get_main_content(), unsafe_allow_html=True)
    st.markdown(get_markdown_content(), unsafe_allow_html=True)
    st.write(get_footer_content(), unsafe_allow_html=True)
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
