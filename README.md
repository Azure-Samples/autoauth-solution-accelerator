# 🤖 AutoAuth: Streamlining Prior Authorization with Azure AI

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![AI](https://img.shields.io/badge/AI-enthusiast-7F52FF.svg)
![GitHub stars](https://img.shields.io/github/stars/pablosalvador10/gbb-ai-hls-factory-prior-auth?style=social)
![Issues](https://img.shields.io/github/issues/pablosalvador10/gbb-ai-hls-factory-prior-auth)
![License](https://img.shields.io/github/license/pablosalvador10/gbb-ai-hls-factory-prior-auth)

[![Deploy to Azure with AZD](https://aka.ms/deploytoazurebutton)](#end-to-end-deployment-using-azd)

## 📚 Table of Contents

- [Overview](#-overview)
- [Introducing AutoAuth](#-introducing-autoauth)
- [Why This Repository?](#-why-this-repository)
- [Quick Start](#-quick-start)
    - [End-to-End Deployment Using AZD](#end-to-end-deployment-using-azd)
    - [PriorAuth SDK](#priorauth-sdk)
- [What's Next?](#-whats-next)
- [Contributors & License](#-contributors--license)

## 🌍 Overview

Prior Authorization (PA) is a critical step in healthcare delivery, requiring providers to seek approval from payors before offering certain treatments. While essential for cost control and care management, the current PA process is often manual, fragmented, and time-consuming:

- **Provider Burden**: Physicians handle an average of **41 PA requests per week**, consuming **13 hours**—almost two full working days—leading to high administrative burdens (88% of physicians report it as high or extremely high). [\[1\]](https://www.ama-assn.org/)
- **Payor Costs**: Up to 75% of PA tasks are manual, costing around **$3.14 per request**, and can be reduced by up to 40% through AI-driven automation. [\[2\]](https://sagilityhealth.com/) [\[3\]](https://www.mckinsey.com/)
- **Patient Outcomes**: **93% of physicians** state PA delays necessary care, and **82% of patients** sometimes abandon treatments due to these delays. Even a one-week delay in critical treatments like cancer can increase mortality risk by 1.2–3.2%. [\[1\]](https://www.ama-assn.org/) [\[3\]](https://www.mckinsey.com/)

This repository aims to **streamline and automate** the PA process using Azure AI, Agentic workflows, and advanced reasoning models. By leveraging machine learning, OCR, and agentic retrieval-augmented generation (RAG), we can reduce human labor, cut costs, and ultimately improve patient care.

![PA Workflow](utils/images/paworflow.png)

**Note:** Our methodology, developed in collaboration with clinicals experts (MD and PharmD), is research-based and includes comprehensive case studies. For an in-depth understanding, please refer to our [article on Hashnode.](https://pabloaicorner.hashnode.dev/streamlining-prior-authorization-with-generative-ai).

## 🤖 Introducing AutoAuth

**AutoAuth** revolutionizes the Prior Authorization process through:

- **Intelligent Document Analysis**: OCR and LLM-driven extraction of clinical details from various document types.
- **Smart Policy Matching**: Agentic Rag laveraging Hybrid retrieval systems (Vector + BM25) identify relevant policies and criteria swiftly.
- **Advanced Reasoning Models**: Assess compliance against policies, recommend Approve/Deny decisions, or request additional info with full traceability.

![Solution Diagram](utils/images/diagram_latest.png)


**Note:** For comprehensive details, including technical architecture, customization steps, references, and additional documentation, please visit our **[GitHub Pages](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**.

## 🎉 Why This Repository?

1. **Faster Decisions & Cost Efficiency**:
   Transform days-long PA turnarounds into hours, drastically reducing administrative overhead and associated costs.

2. **Improved Patient Outcomes**:
   Accelerate treatment approvals, minimize delays in critical care, and enhance overall patient satisfaction.

3. **Automated Infrastructure**:
   Utilize pre-built Azure Bicep templates and one-click deployment to set up the necessary infrastructure—Azure OpenAI, Storage, Cognitive Services—without manual, time-consuming configurations.

4. **LLMOps & Evaluation with AI Foundry**:
   Leverage Azure AI Foundry for continuous model performance evaluation and prompt optimization. Implement robust LLMOps practices, ensuring consistent improvements in accuracy and reliability over time.

5. **Agentic Interactions via Semantic Kernel**:
   Integrate Semantic Kernel to enable agentic interactions with the LLM, coordinating policy retrieval, data extraction, and decision-making steps efficiently and autonomously.

6. **Research-Proven Prompts & Fine-Tuning**:
   Benefit from research-backed prompt engineering strategies that improve precision and reduce hallucinations in model outputs, ensuring that the system’s recommendations align closely with clinical and policy requirements.

## 🚀 Quick Start

> [!TIP]
> *Want to customize or learn more about configuration?*
> **[Read the detailed instructions on our GitHub Pages ➜](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**

To deploy this project end-to-end (infra provision and app deploy) using AZD, follow the guide provided in:
### End-to-End Deployment Using AZD
More detailed documentation can be found in [docs/azd_deployment.md](docs/azd_deployment.md).

### Steps to Deploy

1. **Ensure Necessary Permissions**:
    - You need `Contributor` permissions to provision resources.
    - You need `User Access Administrator` permissions to assign roles to the user-assigned identity.

2. **Install Azure Developer CLI**:
    - Follow the [installation guide](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd).

3. **Initialize Environment**:
    - Run `azd init` to set up your Azure Developer CLI environment.

4. **Deploy**:
    - Execute `azd up` to deploy the project.

5. **Verify Deployment**:
    - Use `azd show` to confirm your deployment.

### Customizing or Configuring the AZD Deployment

- **Main Workflow Definition**:
    - [azure.yaml](./azure.yaml): Defines how `azd` will behave (pre/post hooks, infra definition, app deployment, etc.).

- **Pre/Post Provision and Deployment Scripts**:
    - [utils/azd/hooks](./utils/azd/hooks/): Contains script definitions.
        - `postprovision` scripts populate your `.env` file for local testing.

- **Infra Bicep Definitions**:
    - [infra/main.bicep](infra/main.bicep): Main entry point azd hooks into. Currently scoped to the subscription to automate the provisioning of the resource group. The `outputs` defined in this file become accessible within your azd environment (retrievable via `azd env get-values`).
    - [infra/resources.bicep](infra/resources.bicep): The primary resources for this deployment are stored here.
    - [infra/main.parameters.json](infra/main.parameters.json): Holds the current default values for the deployment and supports overriding the values from ENV vars.
    - To test the infra provisioning without deploying the application, you can do so via `azd provision`.

- **Application Definitions**:
    - AZD handles the deployment of your app image to the newly provisioned container registry/container apps/container app job.
    - These applications map to the provisioned infra resources through tags, specifically using the service name as defined in [azure.yaml](./azure.yaml).

        ```yaml
        services:
            frontend:
                project: app/frontend
                host: containerapp
                language: python
                docker:
                    path: Dockerfile
                    context: ../../
                    remoteBuild: true
        ```

        - `services`: Root element for service definitions.
            - `frontend`: Name of the service.
                - `project`: Path to the frontend project directory.
                - `host`: Hosting environment for the service (e.g., containerapp).
                - `language`: Programming language used for the service (e.g., python).
                - `docker`: Docker configuration for the service.
                    - `path`: Path to the Dockerfile.
                    - `context`: Build context for Docker.
                    - `remoteBuild`: Indicates if the build should be performed remotely.

        ```arm
        module frontendContainerApp 'br/public:avm/res/app/container-app:0.11.0' = {
            ...

            tags: union(tags, { 'azd-service-name': 'frontend' })
        }
        ```
        - `module frontendContainerApp`: Defines the ARM module for the frontend container app.
            - `tags`: Metadata tags for the container app, including the service name.
                - `'azd-service-name'`: Tag to identify the service name (e.g., 'frontend').

    - If you would like to test just the application deployment, you can do so via `azd deploy <service name>` (e.g., `azd deploy frontend`).

### PriorAuth SDK

You can seamlessly integrate Prior Authorization (PA) processing into your application using our SDK. The SDK allows you to run PA workflows programmatically, enabling you to automate the end-to-end process.

#### Example Usage

```python
from src.pipeline.paprocessing.run import PAProcessingPipeline

# Instantiate the PA processing pipeline
pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)

# Run the pipeline with uploaded files
await pa_pipeline.run(uploaded_files=files, use_o1=True)
```
> [!TIP]
> To test the PA processing pipeline and get started, please refer to the notebook [`02-test-pa-workflow.ipynb`](./02-test-pa-workflow.ipynb).

#### ⚙️ Build and Expand the SDK

For those looking for greater flexibility, the AutoAuth SDK enables you to embed PA microservices into your existing applications. You can customize, integrate, and extend the PA workflows to suit your specific needs. This approach provides a highly modular, code-first experience for developers who want to build their own solutions.

#### Key Features of the AutoAuth SDK

- 📡 **Plug-and-Play API Integration with FastAPI**: Quickly expose Prior Authorization (PA) workflows as REST APIs, enabling system-to-system integrations.
- 🔄 **Modular and Extensible for Custom PA Workflows**: Customize and extend the SDK to fit your business logic and workflows.
- ⚡ **Rapid Deployment and Integration**: Minimal setup required to start automating PA workflows. Use FastAPI or other framework to expose endpoints and interact with the PA logic programmatically.

With the AutoAuth SDK, you have the flexibility to automate end-to-end Prior Authorization workflows or select specific components to integrate into your system. Whether you require a full application or a microservice solution, AutoAuth provides the tools you need.


## ✅ What's Next?

### Near-Term Goals.
- [ ] **Improve One-Click Deployment with Integrated Security and Landing Zone**: Enhance a one-click deployment solution a managed landing zone for streamlined setup and management.
- [ ] **Multi-Language & Region Support**: Adapt LLM models and policies for multiple languages and healthcare regulatory environments.
- [ ] **Agentic Framework Leveraging Semantic Kernel**: Integrate the Agentic framework component using the Semantic Kernel as the core for context-aware and intelligent agent orchestration.
- [ ] **API Management (APIM) Integration**: Introduce APIM for secure, scalable, and controlled access to the service’s endpoints.
- [ ] **Deeper LLMOps with AI Foundry**: Extend AI Foundry integration for advanced model lifecycle management, enhanced logging, continuous monitoring, and end-to-end orchestration.

## 🤝 Contributors & License

### Contributors

<table>
<tr>
    <td align="center" style="word-wrap: break-word; width: 150px; height: 150px">
        <a href=https://github.com/pablosalvador10>
            <img src=https://avatars.githubusercontent.com/u/31255154?v=4 width="100" style="border-radius:50%;padding-top:10px" alt="Pablo Salvador Lopez"/>
            <br />
            <sub style="font-size:14px"><b>Pablo Salvador Lopez</b></sub>
        </a>
    </td>
    <td align="center" style="word-wrap: break-word; width: 150px; height: 150px">
        <a href=https://github.com/marcjimz>
            <img src=https://avatars.githubusercontent.com/u/94473824?v=4 width="100" style="border-radius:50%;padding-top:10px" alt="Jin Lee"/>
            <br />
            <sub style="font-size:14px"><b>Jin Lee</b></sub>
        </a>
    </td>
    <td align="center" style="word-wrap: break-word; width: 150px; height: 150px">
        <a href=https://github.com/marcjimz>
            <img src=https://avatars.githubusercontent.com/u/4607826?v=4 width="100" style="border-radius:50%;padding-top:10px" alt="Marcin Jimenez"/>
            <br />
            <sub style="font-size:14px"><b>Marcin Jimenez</b></sub>
        </a>
    </td>
</tr>
</table>

**License:** [MIT License](./LICENSE)

---

**Note:** Detailed information, technical architecture, customization steps, references, and further documentation are available on our **[GitHub Pages](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**.
