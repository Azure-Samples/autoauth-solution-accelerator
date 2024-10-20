# Azure AI Solutions Quick Start Template <img src="./utils/images/azure_logo.png" alt="Azure Logo" style="width:30px;height:30px;"/>

Welcome to the Azure AI Solutions Quick Start Template! This repository is designed to be a rapid launchpad for your Azure AI projects. Whether you're working in an enterprise or academic environment, this template integrates best practices to ensure a smooth development journey from start to finish.

## 💼 Using this Template: Your Gateway to Advanced AI Development & Collaboration!

- **🔄 Development Workflow**: Get to know our optimized workflow, designed to foster effective collaboration and a focus on product-centric development. See our [CONTRIBUTING GUIDE](./CONTRIBUTING.md) for more details.

- **🚀 Advanced AI Development Process**: Understand the specifics of managing Azure AI projects, from issue reporting to pull requests, while adhering to best practices in advanced feature development and complex system troubleshooting.

- **🔍 Testing & QA for AI Systems**: Learn about the importance of rigorous testing in AI projects and discover efficient development and testing techniques tailored for AI systems with tools like Jupyter Notebooks and `%%ipytest`.

- **🔢 Version & Branching Strategies for AI Projects**: Get to know our versioning system and explore the project’s branching strategy, which ensures smooth transitions between development, staging, and production, especially for AI-driven applications.

- To stay updated with the latest developments and document significant changes to this project, please refer to [CHANGELOG.md](CHANGELOG.md).

## Requirements

> Modify as needed by project 

### Setting Up Azure AI Services

- Azure OpenAI Service: You need to create an Azure OpenAI service instance and obtain the API key. [start here](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- Azure Speech AI Service: Required for speech-to-text conversion. Set up the service and get the subscription key and region. [start here](https://azure.microsoft.com/en-us/products/ai-services/ai-speech)
- Azure Language Service: Necessary for language understanding and intent recognition.[start here](https://azure.microsoft.com/en-us/products/ai-services/ai-language)

### Configuration Env variables

We will now use environment variables to store our configuration. This is a more secure practice as it prevents sensitive data from being accidentally committed and pushed to version control systems.

Create a `.env` file in your project root and add the following variables:

```env
# Your Azure Speech Service subscription key
SPEECH_KEY=<Your_Azure_Speech_Service_Subscription_Key>

# Your Azure Speech Service region
SPEECH_REGION=<Your_Azure_Speech_Service_Region>

# Your Azure Machine Learning workspace key
INTENT_KEY=<Your_Azure_Machine_Learning_Workspace_Key>

# Your Azure OpenAI API key
OPENAI_KEY=<Your_Azure_OpenAI_API_Key>

# The model used for chat
CHAT_MODEL=<Your_Chat_Model>

# The model used for completions
COMPLETION_MODEL=<Your_Completion_Model>

# The base URL for the OpenAI API
OPENAI_API_BASE=<Your_OpenAI_API_Base_URL>

# The version of the OpenAI API
OPENAI_API_VERSION=<Your_OpenAI_API_Version>

# Your Azure Storage connection string
AZURE_STORAGE_CONNECTION_STRING=<Your_Azure_Storage_Connection_String>
``` 

`SPEECH_KEY` and `SPEECH_REGION` are used for the Azure Speech Service.
`INTENT_KEY` is used for the Azure Machine Learning workspace.
`OPENAI_KEY`, `CHAT_MODEL`, `COMPLETION_MODEL`, `OPENAI_API_BASE`, and `OPENAI_API_VERSION` are used for the Azure OpenAI API.
`AZURE_STORAGE_CONNECTION_STRING` is used for Azure Storage.

> 📌 Note Remember not to commit the .env file to your version control system. Add it to your .gitignore file to prevent it from being tracked.

## 🌲 Project Tree Structure

```markdown
📂 gbbai-azure-ai-template
┣ 📂 notebooks <- For development, EDA, and quick testing (Jupyter notebooks for analysis and development).
┣ 📂 src <- Houses main source code for data processing, feature engineering, modeling, inference, and evaluation.
┣ 📂 test <- Runs unit and integration tests for code validation and QA.
┣ 📂 utils <- Contains utility functions and shared code used throughout the project.
┣ 📜 .env.sample <- Sample environment variables file. Replace with your own.
┣ 📜 .pre-commit-config.yaml <- Config for pre-commit hooks ensuring code quality and consistency.
┣ 📜 01-workshop.ipynb <- Jupyter notebook for the workshop.
┣ 📜 CHANGELOG.md <- Logs project changes, updates, and version history.
┣ 📜 USAGE.md <- Guidelines for using this template.
┣ 📜 environment.yaml <- Conda environment configuration.
┣ 📜 Makefile <- Simplifies common development tasks and commands.
┣ 📜 pyproject.toml <- Configuration file for build system requirements and packaging-related metadata.
┣ 📜 README.md <- Overview, setup instructions, and usage details of the project.
┣ 📜 requirements-codequality.txt <- Requirements for code quality tools and libraries.
┣ 📜 requirements.txt <- General project dependencies.
```