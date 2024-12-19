# 🚀 Streamlining Prior Authorization with Azure AI

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![AI](https://img.shields.io/badge/AI-enthusiast-7F52FF.svg)
![GitHub stars](https://img.shields.io/github/stars/pablosalvador10/gbbai-azure-ai-capacity?style=social)
![Issues](https://img.shields.io/github/issues/pablosalvador10/gbbai-azure-ai-capacity)
![License](https://img.shields.io/github/license/pablosalvador10/gbbai-azure-ai-capacity)

> [!NOTE]
> Want to get started right away? Deploy with your OpenAI-enabled Azure subscription today!

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)

## 🌍 Overview

Prior Authorization (PA) is a critical step in healthcare delivery, requiring providers to seek approval from payors before offering certain treatments. While essential for cost control and care management, the current PA process is often manual, fragmented, and time-consuming:

- **Provider Burden**: Physicians handle an average of **41 PA requests per week**, consuming **13 hours**—almost two full working days—leading to high administrative burdens (88% of physicians report it as high or extremely high). [\[1\]](https://www.ama-assn.org/)
- **Payor Costs**: Up to 75% of PA tasks are manual, costing around **$3.14 per request**, and can be reduced by up to 40% through AI-driven automation. [\[2\]](https://sagilityhealth.com/) [\[3\]](https://www.mckinsey.com/)
- **Patient Outcomes**: **93% of physicians** state PA delays necessary care, and **82% of patients** sometimes abandon treatments due to these delays. Even a one-week delay in critical treatments like cancer can increase mortality risk by 1.2–3.2%. [\[1\]](https://www.ama-assn.org/) [\[3\]](https://www.mckinsey.com/)

This repository aims to **streamline and automate** the PA process using Azure AI, Agentic workflows, and advanced reasoning models. By leveraging machine learning, OCR, and agentic retrieval-augmented generation (RAG), we can reduce human labor, cut costs, and ultimately improve patient care.

![PA Workflow](utils/images/paworflow.png)

## 🤖 Introducing AutoAuth

**AutoAuth** revolutionizes the Prior Authorization process through:

- **Intelligent Document Analysis**: OCR and LLM-driven extraction of clinical details from various document types.
- **Smart Policy Matching**: Hybrid retrieval systems (Vector + BM25) identify relevant policies and criteria swiftly.
- **Advanced Reasoning Models**: Assess compliance against policies, recommend Approve/Deny decisions, or request additional info with full traceability.

![Solution Diagram](utils/images/diagram.png)

## 🎉 Why This Repository?

1. **Faster Decisions & Cost Efficiency**:  
   Transform days-long PA turnarounds into hours, drastically reducing administrative overhead and associated costs.

2. **Improved Patient Outcomes**:  
   Accelerate treatment approvals, minimize delays in critical care, and enhance overall patient satisfaction.

3. **Automated Infrastructure**:  
   Utilize pre-built Azure Bicep templates and one-click deployment to set up the necessary infrastructure—Azure OpenAI, Storage, Cognitive Services—without manual, time-consuming configurations.

4. **LLMOps & Evaluation with AI Studio**:  
   Leverage Azure AI Studio for continuous model performance evaluation and prompt optimization. Implement robust LLMOps practices, ensuring consistent improvements in accuracy and reliability over time.

5. **Agentic Interactions via Semantic Kernel**:  
   Integrate Semantic Kernel to enable agentic interactions with the LLM, coordinating policy retrieval, data extraction, and decision-making steps efficiently and autonomously.

6. **Research-Proven Prompts & Fine-Tuning**:  
   Benefit from research-backed prompt engineering strategies that improve precision and reduce hallucinations in model outputs, ensuring that the system’s recommendations align closely with clinical and policy requirements.

## 🚀 Quick Start: One-Click Deploy

Ready to dive in? With just one click, you can deploy the core infrastructure and start exploring the solution.

[![Deploy To Azure](utils/images/deploytoazure.svg?sanitize=true)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)
[![Visualize](utils/images/visualizebutton.svg?sanitize=true)](http://armviz.io/#/?load=https%3A%2F%2Fraw.githubusercontent.com%2Fpablosalvador10%2Fgbb-ai-hls-factory-prior-auth%2Fdevops%2Finfra%2Fmain.json)

> [!TIP]
> *Want to customize or learn more about configuration?*  
> **[Read the detailed instructions on our GitHub Pages ➜](https://pablosalvador10.github.io/gbb-ai-hls-factory-prior-auth)**

## ✅ What's Next?

### Near-Term Goals
- [ ] **Public Image Availability**: Host container images publicly (e.g., on GitHub Container Registry) for easier and more flexible deployments.
- [ ] **Multi-Language & Region Support**: Adapt LLM models and policies for multiple languages and healthcare regulatory environments.  
- [ ] **API Management (APIM) Integration**: Introduce APIM for secure, scalable, and controlled access to the service’s endpoints.  
- [ ] **Deeper LLMOps with AI Studio**: Extend AI Studio integration for advanced model lifecycle management, enhanced logging, continuous monitoring, and end-to-end orchestration.

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