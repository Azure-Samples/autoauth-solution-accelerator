# 🤖 AutoAuth: Streamlining Prior Authorization with Azure AI

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![AI](https://img.shields.io/badge/AI-enthusiast-7F52FF.svg)
![GitHub stars](https://img.shields.io/github/stars/pablosalvador10/gbb-ai-hls-factory-prior-auth?style=social)
![Issues](https://img.shields.io/github/issues/pablosalvador10/gbb-ai-hls-factory-prior-auth)
![License](https://img.shields.io/github/license/pablosalvador10/gbb-ai-hls-factory-prior-auth)

> 🚀 **Welcome! Ready to streamline your Prior Authorization process?** Click below to get started with your deployment and unlock the full potential of AutoAuth.


<div align="center">
    <a href="https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth/azd_deployment.html">
        <img src="https://img.shields.io/badge/🚀%20Click Me-Deploy%20To%20Azure-blue?style=for-the-badge&logo=github&logoWidth=20" alt="📚 Wiki" height="32">
    </a>
    </a>
</div>

## 📚 Table of Contents

- [Overview](#-overview)
- [Introducing AutoAuth](#-introducing-autoauth)
- [Why This Repository?](#-why-this-repository)
- [Quick Start](#-quick-start)
    - [End-to-End Deployment Using AZD](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth/azd_deployment.html)
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


### End-to-End Deployment Using AZD


> [!TIP]
> *Want to customize or learn more about configuration?*
> **[Read the detailed instructions on our GitHub Pages ➜](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**

More detailed documentation can be found in [docs/azd_deployment.md](docs/azd_deployment.md).

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
- [x] **Improve One-Click Deployment with Integrated Security and Landing Zone**: Enhance a one-click deployment solution a managed landing zone for streamlined setup and management.
- [ ] **Multi-Language & Region Support**: Adapt LLM models and policies for multiple languages and healthcare regulatory environments.
- [ ] **Agentic Framework Leveraging Semantic Kernel**: Integrate the Agentic framework component using the Semantic Kernel as the core for context-aware and intelligent agent orchestration.
- [ ] **API Management (APIM) Integration**: Introduce APIM for secure, scalable, and controlled access to the service’s endpoints.
- [ ] **Deeper LLMOps with AI Foundry**: Extend AI Foundry integration for advanced model lifecycle management, enhanced logging, continuous monitoring, and end-to-end orchestration.

## 🤝 Contributors & License

Please read through our [contributing guidelines](./CONTRIBUTING.md). Directions are included for opening issues, coding standards, and notes on development.

### 💻 Steering Committee

|                                                                                                                                                                                                                                                                        |                                                                                                                                                                                                                                         |                                                                                                                                                                                                                                            |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <a href="https://github.com/pablosalvador10"><img src="https://avatars.githubusercontent.com/u/31255154?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Pablo Salvador Lopez](https://github.com/pablosalvador10)** <br> *App Development WG* | <a href="https://github.com/marcjimz"><img src="https://avatars.githubusercontent.com/u/4607826?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Marcin Jimenez](https://github.com/marcjimz)** <br> *AIOps WG* | <a href="https://github.com/marcjimz"><img src="https://avatars.githubusercontent.com/u/94473824?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Jin Lee](https://github.com/marcjimz)** <br> *App Deployment WG* |

### ✨ Contributions

💙 *We appreciate all contributors for their internal and external efforts to this repository in making this project the impactful way it is, without you AutoAuth would not be what it is today!*

|  |  |  |  |  |
|---|---|---|---|---|
| <a href="https://github.com/naren-msft"><img src="https://avatars.githubusercontent.com/u/84394081?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Narendra Amirineni](https://github.com/naren-msft)** | <a href="https://github.com/jkaresha"><img src="https://avatars.githubusercontent.com/u/780467?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Joe Karasha](https://github.com/joe-Karasha)** | <a href="https://github.com/juan-trujillo"><img src="https://avatars.githubusercontent.com/u/6484680?v=4" width="100" style="border-radius:50%;padding-top:10px"></a> <br> **[Juan Trujillo](https://github.com/juan-trujillo)** |  |  |

**License:** [MIT License](./LICENSE)

---

**Note:** Detailed information, technical architecture, customization steps, references, and further documentation are available on our **[GitHub Pages](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**.
