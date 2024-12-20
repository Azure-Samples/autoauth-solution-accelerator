# 🤖 AutoAuth: Streamlining Prior Authorization with Azure AI

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![AI](https://img.shields.io/badge/AI-enthusiast-7F52FF.svg)
![GitHub stars](https://img.shields.io/github/stars/pablosalvador10/gbb-ai-hls-factory-prior-auth?style=social)
![Issues](https://img.shields.io/github/issues/pablosalvador10/gbb-ai-hls-factory-prior-auth)
![License](https://img.shields.io/github/license/pablosalvador10/gbb-ai-hls-factory-prior-auth)

> [!NOTE]
> Want to get started right away? In minutes, deploy with your OpenAI-enabled Azure subscription today!

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)

## 🌍 Overview

Prior Authorization (PA) is a critical step in healthcare delivery, requiring providers to seek approval from payors before offering certain treatments. While essential for cost control and care management, the current PA process is often manual, fragmented, and time-consuming:

- **Provider Burden**: Physicians handle an average of **41 PA requests per week**, consuming **13 hours**—almost two full working days—leading to high administrative burdens (88% of physicians report it as high or extremely high). [\[1\]](https://www.ama-assn.org/)
- **Payor Costs**: Up to 75% of PA tasks are manual, costing around **$3.14 per request**, and can be reduced by up to 40% through AI-driven automation. [\[2\]](https://sagilityhealth.com/) [\[3\]](https://www.mckinsey.com/)
- **Patient Outcomes**: **93% of physicians** state PA delays necessary care, and **82% of patients** sometimes abandon treatments due to these delays. Even a one-week delay in critical treatments like cancer can increase mortality risk by 1.2–3.2%. [\[1\]](https://www.ama-assn.org/) [\[3\]](https://www.mckinsey.com/)

This repository aims to **streamline and automate** the PA process using Azure AI, Agentic workflows, and advanced reasoning models. By leveraging machine learning, OCR, and agentic retrieval-augmented generation (RAG), we can reduce human labor, cut costs, and ultimately improve patient care.

![PA Workflow](utils/images/paworflow.png)

**Note:** Our methodology, developed in collaboration with a clinicals experts (MD and PharmD), is research-based and includes comprehensive case studie. For an in-depth understanding, please refer to our article on Hashnode. [article on Hashnode](https://hashnode.com/draft/67634f1f4a00b0daf47a772f).

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

AutoAuth offers two flexible options to get started:

 + Deploy the Full AutoAuth Application (Front-End + Back-End) with One-Click Deploy
 - Integrate the AutoAuth SDK to Customize and Embed PA Microservices in Your Application

### Option 1: One-Click Deploy (Full Application with UI)

Want to see AutoAuth in action right away? Use the One-Click Deploy option to instantly set up the core infrastructure, including the front-end and back-end, in your Azure environment. With just a single click, you’ll have everything you need to start exploring AutoAuth's end-to-end capabilities.

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)


### Option 2: Use the AutoAuth SDK to Build Custom Microservices

For those looking for greater flexibility, the AutoAuth SDK enables you to embed PA microservices into your existing applications. You can customize, integrate, and extend the PA workflows to suit your specific needs. This approach provides a highly modular, code-first experience for developers who want to build their own solutions.

> [!TIP]
> *Want to customize or learn more about configuration?*  
> **[Read the detailed instructions on our GitHub Pages ➜](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**

You can seamlessly integrate Prior Authorization (PA) processing into your application using our SDK. The SDK allows you to run PA workflows programmatically, enabling you to automate the end-to-end process.

#### Example Usage

```python
from src.pipeline.paprocessing.run import PAProcessingPipeline

# Instantiate the PA processing pipeline
pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)

# Run the pipeline with uploaded files
await pa_pipeline.run(uploaded_files=files, use_o1=True)
```

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

### Disclaimer
> [!IMPORTANT]
> This software is provided for demonstration purposes only. It is not intended to be relied upon for any purpose. The creators of this software make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability or availability with respect to the software or the information, products, services, or related graphics contained in the software for any purpose. Any reliance you place on such information is therefore strictly at your own risk.