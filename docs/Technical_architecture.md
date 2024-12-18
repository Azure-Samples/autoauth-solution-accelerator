---
layout: default
title: "Technical Architecture"
nav_order: 4
---

# ⚙️ Technical Architecture  

This page describes the end-to-end architecture powering **AutoAuth**.

---

## **Architecture Overview**  

- **Document Ingestion**: Azure Blob Storage.  
- **Processing**: OCR via Azure Document Intelligence.  
- **Indexing**: Azure Cognitive Search for hybrid retrieval.  
- **Reasoning**: Azure OpenAI LLM models for policy decision-making.  

---

## 🛠️ **Key Components**  

| **Component**                   | **Description**                         |  
|---------------------------------|-----------------------------------------|  
| Azure OpenAI Service            | GPT-4o for reasoning and query logic    |  
| Azure Search                    | Hybrid vector and lexical retrieval     |  
| Document Intelligence           | OCR for extracting structured data      |  
| Azure Storage                   | Stores raw and processed documents      |  

---

![Architecture Diagram](./_assets/images/technical_diagram.png){: width="600" align="center"}

---
