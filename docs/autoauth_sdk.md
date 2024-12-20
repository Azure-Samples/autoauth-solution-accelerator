---
layout: default
title: "AutoAuth SDK"
nav_order: 4
---

# Getting Started with the AutoAuth SDK

For those seeking greater flexibility, the **AutoAuth SDK** enables you to embed Prior Authorization (PA) microservices into your existing applications. You can customize, integrate, and extend PA workflows to suit your specific needs. This approach provides a highly modular, code-first experience for developers who want to build their own solutions.

## ⚙️ Build and Expand the SDK

The AutoAuth SDK allows you to integrate Prior Authorization workflows directly into your applications. Customize, extend, and tailor the PA workflows to meet your specific requirements, providing a modular and code-first experience for developers.

### Key Features of the AutoAuth SDK

- 📡 **Plug-and-Play API Integration with FastAPI**: Quickly expose Prior Authorization workflows as REST APIs, enabling seamless system-to-system integrations.
- 🔄 **Modular and Extensible Architecture**: Customize and extend the SDK to fit your business logic and workflows.
- ⚡ **Rapid Deployment and Integration**: Minimal setup required to start automating PA workflows. Use FastAPI or other frameworks to expose endpoints and interact with the PA logic programmatically.

With the AutoAuth SDK, you have the flexibility to automate end-to-end Prior Authorization workflows or integrate specific components into your system. Whether you need a full application or a microservice solution, AutoAuth provides the tools you need.

---

## 🚀 Setup Instructions

Follow these step-by-step instructions to set up the AutoAuth SDK and ensure proper configuration.

### Step 1: Set Up Environment Variables

#### Locate the Sample Environment File

- In the root directory of the repository, locate the file named `.env.sample`.

#### Create Your Environment Configuration

- Make a copy of `.env.sample` and rename it to `.env`.

#### Populate the `.env` File

- Open the `.env` file in a text editor.
- Replace placeholder values with your actual configuration details. Example variables include API keys, connection strings, and service endpoints.
- Ensure all required variables are set to avoid runtime errors.

> ⚠️ **Important:** Handle the `.env` file securely, as it contains sensitive information.

---

### Step 2: Set Up Required Azure Services

> **Note:** If you prefer to deploy the entire infrastructure with one click, please refer to the [Deployment Guide](deployment.md).

To obtain the necessary configuration details for the `.env` file, you’ll need to set up the following Azure services:

1. **Azure OpenAI Service**
   - **Setup Guide:** [Get started with Azure OpenAI Service](https://learn.microsoft.com/azure/cognitive-services/openai/quickstart)

2. **Azure Cognitive Search**
   - **Setup Guide:** [Create an Azure Cognitive Search service](https://learn.microsoft.com/azure/search/search-create-service-portal)

3. **Azure Blob Storage**
   - **Setup Guide:** [Create a storage account](https://learn.microsoft.com/azure/storage/common/storage-account-create)

4. **Azure Cosmos DB**
   - **Setup Guide:** [Create an Azure Cosmos DB account](https://learn.microsoft.com/azure/cosmos-db/create-sql-api-dotnet)

5. **Azure AI Document Intelligence (formerly Form Recognizer)**
   - **Setup Guide:** [Quickstart: Form Recognizer client library](https://learn.microsoft.com/azure/applied-ai-services/form-recognizer/quickstarts/get-started-sdk-form-recognizer)

6. **Azure Application Insights**
   - **Setup Guide:** [Set up Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/create-new-resource)

---

### Step 3: Index Policies

#### Run Policy Indexing Notebook

- Open the notebook `01-indexing-policies.ipynb`.

- Run all cells to index policy documents into the Azure Cognitive Search service.

#### Validate the Indexing Process

- Ensure the indexing completes without errors.

> 💡 **Tip:** Proper indexing ensures accurate policy retrieval during the Prior Authorization process.

---

### Step 4: Data Sources

#### Locate Test Cases

- **Directory**: Test and validation cases are stored in the `utils/data/` directory.

#### Review Example Cases

- Sample files (e.g., `001`) contain clinical references and required documentation for Prior Authorization.
- These samples help in understanding the data structure and testing the application's functionality.

> **Note:** These data files have been created and validated by certified physicians (MD certified) to ensure accuracy and reliability.

---

### Step 5: Developer Notes

#### Test the Pipeline

Developers can test the Prior Authorization (PA) processing pipeline using the following code:

```python
from src.pipeline.paprocessing.run import PAProcessingPipeline

# Instantiate the PA processing pipeline
pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)

# Example list of uploaded files to process
uploaded_files = [
    # Replace with your actual file paths or file objects
    "utils/data/001/clinical_document.pdf",
    "utils/data/001/supporting_documentation.pdf"
]

# Run the pipeline with the uploaded files
await pa_pipeline.run(uploaded_files=uploaded_files, use_o1=True)
```