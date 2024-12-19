---
layout: default
title: "Technical Architecture"
nav_order: 4
---

# ⚙️ Technical Architecture

AutoAuth’s architecture orchestrates multiple Azure services and techniques to seamlessly process requests, retrieve policies, and generate recommendations.

![Architecture](./images/diagram.png)

## High-Level Overview

- **Document Ingestion**: Store unstructured documents in Azure Blob Storage.
- **Processing & Extraction**: Apply OCR with Azure Document Intelligence to transform scanned documents into machine-readable text.
- **Indexing & Retrieval**: Use Azure Cognitive Search with a hybrid approach (vector embeddings + BM25) to find relevant policy documents.
- **Reasoning**: Leverage Azure OpenAI to evaluate policies against clinical inputs, guided by agentic pipelines (Semantic Kernel).

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