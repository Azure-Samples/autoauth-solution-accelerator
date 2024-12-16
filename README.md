# Streamlining Prior Authorization with Azure AI <img src="./utils/images/azure_logo.png" alt="Azure Logo" style="width:30px;height:30px;vertical-align:sub;"/>

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![AI](https://img.shields.io/badge/AI-enthusiast-7F52FF.svg)
![GitHub stars](https://img.shields.io/github/stars/pablosalvador10/gbbai-azure-ai-capacity?style=social)
![Issues](https://img.shields.io/github/issues/pablosalvador10/gbbai-azure-ai-capacity)
![License](https://img.shields.io/github/license/pablosalvador10/gbbai-azure-ai-capacity)

Prior Authorization (PA) is a process in healthcare where providers must seek approval from payors (insurance companies) before delivering specific treatments or medications. While essential for cost control and care management, the process has become inefficient, creating substantial delays, administrative overheads, and negative outcomes for all stakeholders—providers, payors, and patients.

![alt text](utils/images/paworflow.png)

### 🔍 Identifying Challenges and Leveraging Opportunities

Let's uncover the daily pain points faced by providers and payors, and understand the new landscape for Prior Authorization (PA) with the upcoming 2026 regulations.

<details>
<summary>📊 Understanding the Burden for Payors and Providers</summary>

<div style="max-height: 400px; overflow-y: auto;">

### ⏳ Time and Cost Implications for Providers and Payors

**Providers:**
- **41 Requests per Week:** Physicians handle an average of 41 PA requests per week, consuming around 13 hours, equivalent to two business days [1].
- **High Administrative Burden:** 88% of physicians report a high or extremely high administrative burden due to PA processes [1].

**Payors:**
- **Manual Processing Costs:** Up to 75% of PA tasks are manual or partially manual, costing around $3.14 per transaction [2].
- **Automation Benefits:** AI can reduce processing costs by up to 40%, cutting manual tasks and reducing expenses to just pennies per request in high-volume cases [2][3].

### 🚨 Impact on Patient Outcomes and Delays

**Providers:**
- **Treatment Delays:** 93% of physicians report that prior authorization delays access to necessary care, leading to treatment abandonment in 82% of cases [1].
- **Mortality Risk:** Even a one-week delay in critical treatments like cancer increases mortality risk by 1.2–3.2% [3].

**Payors:**
- **Improved Approval Accuracy:** AI automation reduces errors by up to 75%, ensuring more accurate and consistent approvals [2].
- **Faster Turnaround Times:** AI-enabled systems reduce PA decision-making from days to just hours, leading to improved member satisfaction and reduced costs [3].

### ⚙️ Operational Inefficiencies and Automation Potential

**Providers:**
- **Transparency Issues:** Providers often lack real-time insight into PA requirements, resulting in treatment delays. AI integration with EHRs can provide real-time updates, improving transparency and reducing bottlenecks [2].

**Payors:**
- **High-Volume Auto-Approvals:** AI-based systems can automatically approve low-risk cases, reducing call volumes by 10–15% and improving operational efficiency [2][3].
- **Efficiency Gains:** AI automation can save 7–10 minutes per case, compounding savings for payors [3].

### 📊 Key Statistics: AI’s Impact on PA

- 40% cost reduction for payors in high-volume cases using AI automation [3].
- 15–20% savings in call handle time through AI-driven processes [2].
- 75% of manual tasks can be automated [2].
- 88% of physicians report high administrative burdens due to PA [1].
- 93% of physicians report that PA delays patient care [1].

### References

1. American Medical Association, "Prior Authorization Research Reports" [link](https://www.ama-assn.org/practice-management/prior-authorization/prior-authorization-research-reports)
2. Sagility Health, "Transformative AI to Revamp Prior Authorizations" [link](https://sagilityhealth.com/news/transformative-ai-to-revamp-prior-authorizations/)
3. McKinsey, "AI Ushers in Next-Gen Prior Authorization in Healthcare" [link](https://www.mckinsey.com/industries/healthcare/our-insights/ai-ushers-in-next-gen-prior-authorization-in-healthcare)

</div>

</details>

<details>
<summary>🏛️ Impact of CMS (Centers for Medicare & Medicaid Services) New Regulations</summary>

### 🏛️ Impact of CMS (Centers for Medicare & Medicaid Services) New Regulations

**Real-Time Data Exchange:** The new regulations mandate that payors use APIs based on HL7 FHIR standards to facilitate real-time data exchange. This will allow healthcare providers to receive quicker PA decisions—within 72 hours for urgent cases and 7 days for standard requests. Immediate access to PA determinations will dramatically reduce delays, ensuring that patients get the necessary care faster. For AI-driven solutions, this real-time data will enable enhanced decision-making capabilities, streamlining the interaction between payors and providers.

**Transparency in Decision-Making:** Payors will now be required to provide detailed explanations for PA decisions, including reasons for denial, through the Prior Authorization API. This will foster greater transparency, which has been a longstanding issue in the PA process. For AI solutions, this transparency can be leveraged to improve algorithms that predict authorization outcomes, thereby reducing manual reviews and cutting down on administrative burdens. The transparency also enhances trust between providers and payors, reducing disputes over PA decisions.

</details>

---

## The solution: AutoAuth 🤖

![alt text](utils/images/diagram.png)

The **AutoAuth framework** revolutionizes the Prior Authorization (PA) process by integrating Agentic Retrieval-Augmented Generation (RAG) and advanced Large Language Models (LLMs). This approach automates and optimizes key steps in the PA workflow, enhancing decision-making accuracy and efficiency.

AutoAuth employs a three-phase methodology:

1. **Data Extraction and Structuring**
2. **Policy Matching and Hybrid Retrieval**
3. **Advanced Reasoning for Decision Support**

<details>
<summary>📊 In Detail </summary>

<div style="max-height: 400px; overflow-y: auto;">

## Phase 1: Data Extraction and Structuring

This phase focuses on extracting and structuring data from diverse sources using LLM-based Optical Character Recognition (OCR) and agentic pipelines.

- **Data Ingestion and Preprocessing**: The system processes unstructured data (e.g., PDFs, handwritten notes, scanned images) using advanced OCR techniques integrated with RAG agents. This ensures accurate extraction of clinical entities such as ICD-10 codes, lab results, and physician notes.

- **Automated Clinical Information Extraction**: Leveraging LLM-based document processing, the system identifies and extracts clinically relevant entities. Agentic pipelines handle entity resolution and disambiguation, addressing variability in terminology and formatting across different data sources.

- **Data Structuring and Semantic Layering**: Extracted entities are transformed into structured JSON objects with semantic annotations. This standardization ensures consistency and interoperability with downstream components, facilitating precise policy retrieval.

## Phase 2: Policy Matching and Hybrid Retrieval System

In this phase, structured clinical data is matched against policy documents using a hybrid retrieval architecture that combines vector-based semantic search and lexical search methods.

- **Intelligent Query Generation**: The system generates contextually optimized queries using structured clinical data. These queries are enriched by the LLM’s language understanding capabilities, focusing on key clinical entities mapped to policy requirements.

- **Hybrid Vector and Lexical Search**: AutoAuth employs a hybrid retrieval architecture to maximize retrieval accuracy. A dense vector embedding search captures contextual meaning, while a BM25-based lexical search provides precise term-matching for compliance-related keywords. This dual-layered approach allows for fine-grained control in identifying policy documents that best align with the clinical information.

- **Dynamic Policy Ranking and Selection**: Retrieved policies are ranked based on a composite similarity score calculated from both vector and lexical layers. This scoring algorithm prioritizes documents with higher relevance, ensuring that policy documents directly applicable to the case are selected. Advanced ranking metrics, such as cosine similarity in vector space and BM25 relevance scores, drive the final selection.

## Phase 3: Advanced Reasoning for Decision Support

The final phase involves decision-making through a structured reasoning framework that assesses compliance with policy criteria. This phase leverages advanced reasoning models (e.g., OpenAI’s o1-series models) to conduct in-depth policy analysis, enabling comprehensive decision support for PA determination.

- **Policy Criteria Assessment through Complex Reasoning**: Each identified policy criterion is independently evaluated against the extracted clinical information. Using a series of chained inferences, the reasoning model conducts a rigorous analysis to determine if each criterion is fully met, partially met, or unmet. These assessments are grounded in the extracted data and policy requirements, with explicit reasoning chains that simulate human decision-making processes.

- **Identification of Data Gaps and Missing Information**: During the reasoning process, any missing data elements or partially met criteria are flagged. For example, if specific lab results or prior treatment details are absent, the system generates a data request to fill these gaps, thereby ensuring that no authorization decision is made with incomplete information.

- **Decision Recommendation Generation**: Based on the structured analysis, the system generates a decision recommendation—Approve, Deny, or Request Additional Information—using a rules-based logic layer informed by the reasoning model’s assessments. Decisions are accompanied by a detailed rationale, citing specific policy references and clinical data points that substantiate the outcome.

- **Justification and Reporting for Transparent Decision-Making**: The decision and its underlying rationale are encapsulated in a structured report, detailing each policy criterion, the compliance status, and evidence from clinical and policy data. This report is designed for interpretability, ensuring that providers and payers can trace the decision logic and audit the automated process.

## Technical Implementation and Data Complexity

- **Data Variability and Interoperability**:
  - **Variability in Data Formats**: The system handles various document types and qualities, such as scanned images and handwritten notes.
  - **Terminology Disambiguation**: It addresses synonyms, abbreviations, and variations in clinical and policy language.
  - **Interoperability**: Ensures structured data is compatible with downstream systems for seamless integration.

</div>

</details>

---

## One-Click Deploy AutoAuth Framework

We have encapsulated the necessary steps to deploy the assets into Azure, requiring you to bring:

* Azure Subscription
* OpenAI Access
* Available Quota for Resources
* Working Internet Connection
* *Preferred:* Access enabled to deploy `o1-preview` model on Azure OpenAI

> **Temporary:** Ability to build and push Docker images

Try it:

### Step 1. Build the Docker Image

You will need to build the docker image for this repository to work, and you are free to make any changes. You can create the repository on an Azure Container Registry of your choice, similarly:

```bash
docker build -t priorauthdemo.azurecr.io/priorauth-frontend:v1 --file devops/container/Dockerfile .
docker push priorauthdemo.azurecr.io/priorauth-frontend:v1
```

### Step 2. Create the Infrastructure

Included in this repository are our configurations to quickly deploy the infrastructure, you can use `az cli` to create it similarly:

```bash
# May require installing azure-cli-ml extension
# az extension add --name azure-cli-ml
az deployment group create \
    --debug \
    --resource-group "<resourceGroup>" \
    --template-file "devops/infra/main.bicep" \
    --parameters priorAuthName="priorAuth" \
                 tags={} \
                 location="eastus2" \
                 cosmosAdministratorPassword="<password>" \
                 acrContainerImage="priorauthdemo.azurecr.io/priorauth-frontend:v2" \
                 acrUsername="priorauthdemo" \
                 acrPassword="<acrPassword>"
```

Refer to the scripts in `devops/infra/scripts` folder for build and cleanup capabilities.

Alternatively, one-click deployment is possible:

> *Warning*: Templates below will not populate correctly until this repository is made publicly available.

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)

### Step 3: Access Streamlit UI and Upload Policy Documents

Review your deployment and use your browser to navigate to the URL assigned to your container app. Upload your policy documents, and watch AutoAuth work.

## Azure Native Services

The following services are required for implementation.

| **Service Name**         | **Description**                                                                                   | **Major Components**                                              | **Limits/Defaults**                                                                                                  |
|---------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| **Document Intelligence** | Azure Cognitive Services for AI models related to document processing and intelligence.          | `Microsoft.CognitiveServices/accounts`                            | Default SKU: `S0`. Public network access enabled.                                                                    |
| **OpenAI Service**        | Deploys OpenAI models like `GPT-4o` and `text-embedding-ada-002` for completions and embeddings.  | OpenAI deployments: `GPT-4o` (chat), `o1`. `Text Embedding Ada-002` or `text-embedding-3-*`        | `GPT-4o`: Default capacity: 25. `o1` optional and can test with `GPT-4o`.                                                      |
| **Azure Search**          | Azure AI Search service for indexing and querying data.                                          | `Microsoft.Search/searchServices`                                 | Default SKU: `basic`. Public network access enabled.                                                                  |
| **Multi-Service AI**      | General-purpose Cognitive Services account for accessing multiple AI capabilities.               | `Microsoft.CognitiveServices/accounts`                            | Default SKU: `S0`. Public network access enabled. **Must be multi-service.**                                                                   |
| **Storage Account**       | Azure Storage Account for storing and retrieving blob data.                                      | `Microsoft.Storage/storageAccounts`, Blob containers              | Default SKU: `Standard_LRS`. HTTPS traffic only. Delete retention policy: 7 days. Container created named `pre-auth-policies`.                                   |
| **Application Insights**  | Azure monitoring for application performance and availability.                                   | `Microsoft.Insights/components`                                   | Public network access enabled for ingestion and query.                                                               |
| **Cosmos DB (Mongo)**     | Cosmos DB Mongo cluster for storing NoSQL data with high availability.                           | `Microsoft.DocumentDB/mongoClusters`                              | Default compute tier: M30. Storage: 32 GB. Public network access enabled.                                            |
| **Log Analytics**         | Azure Log Analytics for query-based monitoring.                                                  | `Microsoft.OperationalInsights/workspaces`                        | Retention: 30 days.                                                                                                   |
| **Container Apps**        | Azure Container Apps for running microservices and managing workloads.                           | `Microsoft.App/containerApps`, `Microsoft.App/jobs`               | Workload profile: `Consumption`. CPU: 2.0 cores. Memory: 4 GiB per container. Ingress port: 8501.                    |


## Getting Started with AutoAuth Framework

### Step 1: Create and Activate the Conda Environment

#### **For Windows Users**

1. **Create the Conda Environment**:
   - Open your terminal or command prompt and navigate to the repository directory.
   - Run the following command:
     ```bash
     conda env create -f environment.yaml
     ```
   - This command creates the Conda environment as defined in `environment.yaml`.

2. **Activate the Environment**:
   - Once created, activate it using:
     ```bash
     conda activate vector-indexing-azureaisearch
     ```

#### **For Linux Users (or Windows WSL)**

1. **Use `make` for Environment Setup**:
   - Navigate to the repository directory in your terminal.
   - Use the `make` command to create the Conda environment:
     ```bash
     make create_conda_env
     ```

## Step 2: Configure Environment Variables

To ensure the application functions correctly, you need to set up environment variables by following these steps:

1. **Locate the Sample Environment File**:
   - In the root directory of the repository, find the `.env.sample` file.

2. **Create Your Environment Configuration**:
   - Make a copy of `.env.sample` and rename it to `.env`.

3. **Populate the `.env` File**:
   - Open the `.env` file in a text editor.
   - Replace placeholder values with your actual configuration details. For example:

     ```plaintext
     AZURE_OPENAI_KEY=your_azure_openai_key
     AZURE_SEARCH_SERVICE_NAME=your_azure_search_service_name
     AZURE_STORAGE_ACCOUNT_KEY=your_azure_storage_account_key
     ```

   - Ensure all required variables are provided to avoid runtime errors.

**Note**: The `.env` file contains sensitive information. Handle it securely and avoid sharing it publicly.

### Step 3: Index Policies

Before running the application, policies must be indexed to enable accurate search and retrieval.

1. Open the notebook `01-indexing-policies.ipynb`
2. Run all cells to index the policies into the Azure AI Search Service.
3. Ensure indexing completes without errors, as it is essential for retrieving the correct documents during PA processing.

### Step 4: Run the Application

1. Navigate to the repository's root directory.
2. Start the Streamlit application with the following command:
   ```bash
   streamlit run app/streamlit/Home.py
   ```

   > Errors may return on failed import statements on some operating systems, be sure to include the folder path in your `PYTHONPATH` similarly: `export PYTHONPATH=$PYTHONPATH:$(pwd) && python ...`

### Step 5: Data Sources

- Test and validate cases are located in the `utils/data/` directory.
- Example cases (e.g., `001`) include clinical references and documents required for Prior Authorization.

- **Note**: This data has been created and validated by certified physician (MD certified) to ensure accuracy and reliability.

### Step 6: Developer Notes

Developers can test the pipeline for PA processing by instantiating the **PAProcessingPipeline** and running the process with example files.

Example code:
```python
from src.pipeline.paprocessing.run import PAProcessingPipeline

# Instantiate the pipeline
pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)

# Run the pipeline with uploaded files
await pa_pipeline.run(uploaded_files=files, use_o1=True)
```

### Disclaimer
> [!IMPORTANT]
> This software is provided for demonstration purposes only. It is not intended to be relied upon for any purpose. The creators of this software make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability or availability with respect to the software or the information, products, services, or related graphics contained in the software for any purpose. Any reliance you place on such information is therefore strictly at your own risk.

### Contributors

<table>
<tr>
    <td align="center" style="word-wrap: break-word; width: 150.0; height: 150.0">
        <a href=https://github.com/ pablosalvador10>
            <img src=https://avatars.githubusercontent.com/u/31255154?v=4 width="100;"  style="border-radius:50%;align-items:center;justify-content:center;overflow:hidden;padding-top:10px" alt=Pablo Salvador Lopez/>
            <br />
            <sub style="font-size:14px"><b>Pablo Salvador Lopez</b></sub>
        </a>
    </td>
    <td align="center" style="word-wrap: break-word; width: 150.0; height: 150.0">
        <a href=https://github.com/marcjimz>
            <img src=https://avatars.githubusercontent.com/u/94473824?v=4 width="100;"  style="border-radius:50%;align-items:center;justify-content:center;overflow:hidden;padding-top:10px" alt=Jin Lee/>
            <br />
            <sub style="font-size:14px"><b>Jin Lee</b></sub>
        </a>
    </td>
        <td align="center" style="word-wrap: break-word; width: 150.0; height: 150.0">
        <a href=https://github.com/marcjimz>
            <img src=https://avatars.githubusercontent.com/u/4607826?v=4 width="100;"  style="border-radius:50%;align-items:center;justify-content:center;overflow:hidden;padding-top:10px" alt=Marci Jimenezn/>
            <br />
            <sub style="font-size:14px"><b>Marcin Jimenez</b></sub>
        </a>
    </td>
</tr>
</table>
