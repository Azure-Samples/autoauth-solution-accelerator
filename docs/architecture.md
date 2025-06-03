---
layout: default
title: "Technical Architecture"
nav_order: 5
---

# ⚙️ Technical Architecture

AutoAuth’s architecture orchestrates multiple Azure services and techniques to seamlessly process requests, retrieve policies, and generate recommendations.

![Architecture](./images/diagram_latest.png)

## High-Level Overview

- **Knowledge Base Construction**: Establish a centralized repository of Prior Authorization (PA) policies and guidelines to streamline the decision-making process.
- **Unstructured Clinical Data Processing**: Extract and structure patient-specific clinical information from raw data sources using advanced Large Language Model (LLM)-based techniques.
- **Agentic RAG**: Identify the most relevant PA policy for a clinical case using a multi-layered retrieval approach, supported by Azure AI Search and LLM as the formulator and judge, guided by agentic pipelines.
- **Claims Processing**: Leverage Azure OpenAI to evaluate policies against clinical inputs, cross-reference patient, physician, and clinical details against policy criteria. Classify the Prior Authorization (PA) claim as Approved, Denied, or Needs More Information, providing clear, evidence-based explanations and policy references to support a comprehensive human final determination.

## Components

| Component                 | Role                               |
|---------------------------|-------------------------------------|
| Azure OpenAI              | LLMs for reasoning and decision logic |
| Azure Cognitive Search    | Hybrid retrieval (semantic + keyword) |
| Document Intelligence      | OCR and data extraction              |
| Azure Storage             | Document storage                     |
| Azure Bicep Templates     | Automated infrastructure deployment  |
| Semantic Kernel           | Agentic orchestration of retrieval and reasoning |
| Azure AI Studio (LLMOps)  | Model evaluation, prompt optimization, and performance logging |

This integrated design enables a dynamic, AI-driven PA process that is scalable, auditable, and ready for continuous improvement.


# Architecture Overview

AutoAuth is designed with a modular architecture to ensure scalability, maintainability, and extensibility.

## High-Level System Flow

```mermaid
flowchart TB
    Pipeline[pipeline/] --> AOAI[aoai/]
    Pipeline --> CosmosDB[cosmosdb/]
    Pipeline --> DocIntel[documentintelligence/]
    Pipeline --> Search[Azure AI Search SDK]
    Pipeline --> Evals[evals/]

    Evals --> AOAI

    Utils[utils/] -.-> Pipeline
    Utils -.-> AOAI
    Utils -.-> CosmosDB
    Utils -.-> DocIntel
    Utils -.-> Search
```

### Key Components
- **Pipeline**: Orchestrates business logic workflows.
- **AOAI**: Integrates Azure OpenAI for advanced AI capabilities.
- **CosmosDB**: Provides persistent storage for structured data.
- **Document Intelligence**: Extracts structured data from unstructured documents.
- **Azure AI Search SDK**: Enables intelligent policy retrieval.
- **Evals**: Validates pipeline performance and accuracy.
- **Utils**: Shared utilities for logging, configuration, and helpers.

## Pipeline-Centric Architecture

```mermaid
flowchart LR
    subgraph "pipeline/"
        PAProcessing[paprocessing/run.py]
        ClinicalExtractor[clinicalExtractor/run.py]
    end

    subgraph "External Services"
        AOAI[aoai/AzureOpenAIManager]
        Search[Azure Cognitive Search]
    end

    PAProcessing --> AgenticRAG
    PAProcessing --> AutoDetermination
    PAProcessing --> ClinicalExtractor
    PAProcessing --> Storage
    PAProcessing --> CosmosDB

    AgenticRAG --> AOAI
    AgenticRAG --> Search

    PolicyIndexer --> Storage
    PolicyIndexer --> Search
    PolicyIndexer --> DocIntel

    ClinicalExtractor --> DocIntel
    ClinicalExtractor --> AOAI

    AutoDetermination --> AOAI
```

## Data Flow Architecture

```mermaid
flowchart TD
    Upload[Document Upload] --> Storage[storage/AzureBlobManager]
    Storage --> PolicyIndexer[pipeline/policyIndexer/]
    PolicyIndexer --> Search[Azure Cognitive Search]

    Storage --> DocIntel[documentintelligence/]
    DocIntel --> ClinicalExtractor[pipeline/clinicalExtractor/]

    ClinicalExtractor --> AgenticRAG[pipeline/agenticRag/]
    Search --> AgenticRAG
    AgenticRAG --> AOAI[aoai/AzureOpenAIManager]

    AgenticRAG --> AutoDetermination[pipeline/autoDetermination/]
    AutoDetermination --> AOAI

    AutoDetermination --> CosmosDB[cosmosdb/CosmosDBMongoCoreManager]

    subgraph "Evaluation"
        Evals[evals/PipelineEvaluator]
    end

    AgenticRAG --> Evals
    AutoDetermination --> Evals
```

## Next Steps
- Learn more about [Workflows](workflows-overview.md).
- Dive into [Technical Implementation](technical-implementation.md).
- Refer to the [Deployment Guide](azd_deployment.md) for Azure deployment instructions.
