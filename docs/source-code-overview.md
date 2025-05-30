---
layout: default
title: "Source Code Overview"
nav_order: 6
description: "Detailed breakdown of the src directory modules and their interconnections"
---

# AutoAuth Solution Accelerator - Source Code Overview

This directory contains the core business logic and infrastructure for the AutoAuth solution accelerator, organized into modular components that handle different aspects of the automated prior authorization workflow.

## Module Overview

The `src` directory follows a layered architecture with distinct responsibilities:

| Module | Purpose | Key Components |
|--------|---------|----------------|
| **`agenticai/`** | Agentic orchestration and skills management | Agent class, Skills manager, plugins |
| **`aoai/`** | Azure OpenAI integration | AzureOpenAIManager, tokenization utilities |
| **`cosmosdb/`** | Document database operations | CosmosDBMongoCoreManager for data persistence |
| **`documentintelligence/`** | Document processing & OCR | AzureDocumentIntelligenceManager for text extraction |
| **`storage/`** | Blob storage operations | AzureBlobManager for file management |
| **`pipeline/`** | Business logic orchestration | RAG, indexing, PA processing pipelines |
| **`evals/`** | Evaluation framework | PipelineEvaluator, test harnesses |
| **`extractors/`** | Data extraction utilities | PDF processing, OCR helpers |
| **`utils/`** | Shared utilities | Logging, configuration, helpers |

## Architecture Overview

### High-Level System Flow

```mermaid
flowchart TB
    UI[Streamlit UI] --> Pipeline[pipeline/]
    Pipeline --> AgenticAI[agenticai/]
    Pipeline --> AOAI[aoai/]
    Pipeline --> Storage[storage/]
    Pipeline --> DocIntel[documentintelligence/]
    Pipeline --> CosmosDB[cosmosdb/]

    AgenticAI --> AOAI
    DocIntel --> Storage
    Pipeline --> Evals[evals/]

    Utils[utils/] -.-> Pipeline
    Utils -.-> AOAI
    Utils -.-> Storage
    Utils -.-> CosmosDB
```

### Pipeline-Centric Architecture

```mermaid
flowchart LR
    subgraph "pipeline/"
        PAProcessing[paprocessing/run.py]
        AgenticRAG[agenticRag/run.py]
        PolicyIndexer[policyIndexer/run.py]
        AutoDetermination[autoDetermination/run.py]
        ClinicalExtractor[clinicalExtractor/run.py]
    end

    subgraph "External Services"
        AOAI[aoai/AzureOpenAIManager]
        Storage[storage/AzureBlobManager]
        CosmosDB[cosmosdb/CosmosDBMongoCoreManager]
        DocIntel[documentintelligence/AzureDocumentIntelligenceManager]
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

### Data Flow Architecture

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

## Module Detailed Descriptions

### Core Service Modules

#### `aoai/` - Azure OpenAI Integration
- **Purpose**: Manages all interactions with Azure OpenAI services
- **Key Components**:
  - `AzureOpenAIManager`: Main interface for LLM operations
  - Tokenization utilities for prompt optimization
  - Chat completion handling with retry logic
- **Usage**: Used across all pipelines for LLM-powered reasoning, query expansion, and evaluation

#### `storage/` - Azure Blob Storage Management
- **Purpose**: Handles file operations and blob storage interactions
- **Key Components**:
  - `AzureBlobManager`: Core storage operations
  - Upload/download utilities
  - Container management
- **Usage**: Stores policy documents, clinical files, and processed artifacts

#### `cosmosdb/` - Document Database Operations
- **Purpose**: Provides persistent storage for structured data
- **Key Components**:
  - `CosmosDBMongoCoreManager`: Database operations
  - Case management and audit trails
  - Query optimization for large datasets
- **Usage**: Stores case information, processing results, and evaluation metrics

#### `documentintelligence/` - Document Processing
- **Purpose**: Extracts structured data from unstructured documents
- **Key Components**:
  - `AzureDocumentIntelligenceManager`: OCR and entity extraction
  - Image processing utilities
  - Layout analysis capabilities
- **Usage**: Processes clinical documents and policy PDFs for text extraction

### Business Logic Modules

#### `pipeline/` - Core Business Workflows
- **Purpose**: Orchestrates end-to-end business processes
- **Key Components**:
  - `agenticRag/`: Intelligent retrieval and reasoning
  - `policyIndexer/`: Document indexing pipeline
  - `paprocessing/`: Prior authorization workflow
  - `autoDetermination/`: AI-driven decision making
  - `clinicalExtractor/`: Clinical data extraction
  - `promptEngineering/`: Prompt management and optimization

#### `agenticai/` - Agentic AI Framework
- **Purpose**: Provides intelligent agent capabilities with dynamic skill loading
- **Key Components**:
  - `Agent`: Main agent orchestrator
  - `Skills`: Plugin management system
  - Dynamic function calling capabilities
- **Usage**: Enables complex AI workflows with modular, reusable skills

### Support Modules

#### `evals/` - Evaluation Framework
- **Purpose**: Standardized testing and evaluation across all pipelines
- **Key Components**:
  - `PipelineEvaluator`: Base evaluation class
  - Test case management
  - Metrics collection and analysis
- **Usage**: Validates pipeline performance and accuracy

#### `extractors/` - Data Extraction Utilities
- **Purpose**: Specialized data extraction tools
- **Key Components**:
  - PDF processing utilities
  - OCR helpers and optimizations
  - Format conversion tools
- **Usage**: Supporting utilities for document processing workflows

#### `utils/` - Shared Infrastructure
- **Purpose**: Common utilities and configuration management
- **Key Components**:
  - Logging framework (`ml_logging`)
  - Configuration loaders
  - Helper functions
- **Usage**: Foundation layer used across all modules

## Key Interconnection Patterns

### 1. Service Dependencies
All pipeline modules follow a common pattern:
```python
# Common initialization pattern
config = load_config()  # from utils/
aoai_manager = AzureOpenAIManager()  # from aoai/
blob_manager = AzureBlobManager()    # from storage/
cosmos_manager = CosmosDBMongoCoreManager()  # from cosmosdb/
```

### 2. Agentic Orchestration
The agentic framework enables dynamic skill loading:
```python
# Agent instantiation with skills
agent = Agent(skills=["retrieval", "evaluation", "rewriting"])
agent._load_skills()  # Dynamically loads plugin functions
```

### 3. Evaluation Integration
Each pipeline has corresponding evaluators that extend the base framework:
```python
# Standardized evaluation pattern
evaluator = PipelineEvaluator(pipeline_class=AgenticRAG)
results = evaluator.run_evaluation(test_cases)
```

### 4. Configuration Flow
Configuration cascades from utils through all modules:

```mermaid
block-beta
    columns 3
    Config[utils/config] --> Pipeline[pipeline/]
    Config --> Services[Service Modules]
    Pipeline --> Services
    Services --> Evaluation[evals/]
```

## Usage Examples

### Initializing a Complete Pipeline
```python
from src.pipeline.paprocessing.run import PAProcessingPipeline

# Initialize with all dependencies
pipeline = PAProcessingPipeline(
    case_id="TEST-001",
    config_path="config/settings.yaml"
)

# Run end-to-end processing
results = await pipeline.run(
    uploaded_files=["document1.pdf", "document2.pdf"],
    clinical_info="Patient diagnosis and treatment request"
)
```

### Using Individual Components
```python
from src.aoai.aoai_helper import AzureOpenAIManager
from src.storage.blob_helper import AzureBlobManager

# Use individual services
aoai = AzureOpenAIManager()
storage = AzureBlobManager()

# Process documents
blob_url = storage.upload_file("document.pdf")
response = await aoai.chat_completion("Analyze this document")
```

## Best Practices

1. **Modular Design**: Each module has a single responsibility and clear interfaces
2. **Configuration Management**: All settings are externalized to YAML configurations
3. **Error Handling**: Comprehensive logging and error handling across all modules
4. **Async Operations**: Asynchronous programming for better performance
5. **Evaluation-Driven Development**: All pipelines include corresponding evaluation frameworks

## Adding Custom Modules

The AutoAuth solution accelerator is designed to be extensible. You can add your own modules by following these patterns:

### 1. Creating a New Service Module

For new Azure service integrations, follow this structure:

```python
# src/myservice/myservice_manager.py
import logging
from typing import Optional, Dict, Any
from src.utils.ml_logging import get_logger

class MyServiceManager:
    """Manager class for MyService integration."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.logger = get_logger(__name__)
        self.config = config or {}
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the service client."""
        # Your service client initialization
        pass

    async def process_data(self, data: Any) -> Any:
        """Main processing method."""
        try:
            # Your processing logic
            self.logger.info("Processing data with MyService")
            return processed_data
        except Exception as e:
            self.logger.error(f"Error processing data: {e}")
            raise
```

### 2. Creating a New Pipeline Module

For business logic pipelines, create a new directory under `pipeline/`:

```python
# src/pipeline/mypipeline/run.py
from typing import Dict, List, Any
from src.utils.ml_logging import get_logger
from src.aoai.aoai_helper import AzureOpenAIManager
from src.storage.blob_helper import AzureBlobManager

class MyPipeline:
    """Custom pipeline for specific business logic."""

    def __init__(self, config_path: str = None):
        self.logger = get_logger(__name__)
        self.aoai_manager = AzureOpenAIManager()
        self.storage_manager = AzureBlobManager()

    async def run(self, input_data: Any) -> Dict[str, Any]:
        """Execute the pipeline."""
        self.logger.info("Starting MyPipeline execution")

        # Pipeline steps
        step1_result = await self._step_1(input_data)
        step2_result = await self._step_2(step1_result)

        return {
            "status": "completed",
            "results": step2_result
        }

    async def _step_1(self, data: Any) -> Any:
        """First pipeline step."""
        # Implementation
        pass

    async def _step_2(self, data: Any) -> Any:
        """Second pipeline step."""
        # Implementation
        pass
```

### 3. Adding Evaluation Support

Create corresponding evaluators for your modules:

```python
# src/evals/mypipeline_evaluator.py
from src.evals.pipeline_evaluator import PipelineEvaluator
from src.pipeline.mypipeline.run import MyPipeline

class MyPipelineEvaluator(PipelineEvaluator):
    """Evaluator for MyPipeline."""

    def __init__(self):
        super().__init__(pipeline_class=MyPipeline)

    def evaluate_custom_metrics(self, results: Dict) -> Dict[str, float]:
        """Custom evaluation metrics for your pipeline."""
        # Your evaluation logic
        return {
            "custom_metric_1": 0.95,
            "custom_metric_2": 0.87
        }
```

### 4. Configuration Integration

Add your module configuration to the settings files:

```yaml
# Add to appropriate settings.yaml
myservice:
  endpoint: "https://myservice.example.com"
  api_version: "2024-01-01"
  timeout: 30

mypipeline:
  batch_size: 100
  max_retries: 3
  custom_parameter: "value"
```

### 5. Agentic AI Skills Integration

To integrate with the agentic framework, create skill plugins:

```python
# src/agenticai/skills/my_custom_skill.py
from typing import Dict, Any
from src.utils.ml_logging import get_logger

async def my_custom_skill(context: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Custom skill for the agentic framework."""
    logger = get_logger(__name__)

    try:
        # Your skill implementation
        result = process_with_custom_logic(context, **kwargs)

        return {
            "status": "success",
            "result": result,
            "skill_name": "my_custom_skill"
        }
    except Exception as e:
        logger.error(f"Error in custom skill: {e}")
        return {
            "status": "error",
            "error": str(e),
            "skill_name": "my_custom_skill"
        }

def process_with_custom_logic(context: Dict[str, Any], **kwargs) -> Any:
    """Your custom processing logic."""
    # Implementation
    pass
```

### 6. Module Integration Checklist

When adding a new module, ensure you:

- [ ] **Follow naming conventions**: Use descriptive, consistent naming
- [ ] **Add proper logging**: Use the centralized logging framework from `utils/ml_logging`
- [ ] **Include error handling**: Comprehensive try-catch blocks with appropriate logging
- [ ] **Create configuration schema**: Add settings to YAML configuration files
- [ ] **Write unit tests**: Create test files in the `tests/` directory
- [ ] **Add evaluation support**: Create evaluators for pipeline modules
- [ ] **Update documentation**: Add module description to this README
- [ ] **Follow async patterns**: Use async/await for I/O operations
- [ ] **Implement proper initialization**: Follow the established manager class patterns

### 7. Example Integration

Here's how to integrate your new module into existing workflows:

```python
# In your application code
from src.pipeline.mypipeline.run import MyPipeline
from src.myservice.myservice_manager import MyServiceManager

# Initialize your custom components
my_service = MyServiceManager(config=load_config()["myservice"])
my_pipeline = MyPipeline(config_path="config/settings.yaml")

# Use in the main workflow
async def enhanced_workflow():
    # Existing AutoAuth logic
    standard_result = await existing_pipeline.run(data)

    # Your custom enhancement
    custom_result = await my_pipeline.run(standard_result)

    # Additional processing with your service
    final_result = await my_service.process_data(custom_result)

    return final_result
```

This extensible architecture allows you to enhance the AutoAuth solution with domain-specific logic while maintaining consistency with the existing codebase patterns.

This modular architecture enables **separation of concerns**, **reusability**, and **testability** across the entire AutoAuth solution accelerator.

---

{: .note }
> **Source Code Location**: The complete source code with detailed implementation can be found in the [`src/` directory](../src/) of this repository. For the most up-to-date technical details and code examples, refer to the [src/README.md](../src/README.md) file.
