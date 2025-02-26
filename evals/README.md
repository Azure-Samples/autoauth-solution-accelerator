# AutoAuth Evaluation Framework

This repository provides a configuration-driven approach to defining and executing evaluation cases for generative AI tasks within the `AutoAuth` framework. By separating evaluation configurations from the implementation code, the framework promotes flexibility, maintainability, and scalability. Each test case is defined as a YAML configuration file, while the evaluation logic is encapsulated within dedicated Python modules—each containing an `evaluator.py` file.

---

## Overview

The YAML schema is designed to decouple test configurations from the codebase. This enables developers and evaluators to update test parameters, metadata, and evaluation expectations without modifying the underlying pipeline logic. This approach follows best practices observed in systems like Kubernetes and Django, where configurations are externalized for clarity and maintainability.

### Key Advantages

- **Separation of Concerns:**  
  Code handles execution while YAML files drive test definitions.
- **Flexibility:**  
  Each evaluation case can define its own evaluators, arguments, and context to accommodate diverse AI evaluation scenarios.
- **Scalability:**  
  New evaluation cases or modules can be integrated without altering core pipeline code.

---

## Definitive YAML Schema Specification

The YAML configuration files consist of two primary sections:
1. **Test Evaluation Configuration**
2. **Case-Specific Configuration**

### 1. Test Evaluation Configuration

#### Mandatory Fields

| Field           | Description                                                                                                                                                                                                                                                                   | Notes       |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- |
| **description** | - A human-readable explanation of the evaluation’s purpose.                                                                                                                                                                                                                  | Mandatory   |
| **pipeline**    | **Sub-fields:** <br> - **class:** Fully qualified evaluator class name (format: `module_path:ClassName`). <br> - **uploaded_files** / **case_id** / **scenario:** Parameter(s) required by the evaluator.                                                               | Mandatory   |
| **evaluators**  | A list of evaluator definitions. Each evaluator must include: <br> - **type:** Evaluator type (e.g., "azure" or "custom"). <br> - **name:** Unique identifier for the evaluator. <br> - **class:** Fully qualified class reference (format: `module_path:ClassName`). | Mandatory   |
| **cases**       | A list of case identifiers that reference detailed case-specific configurations.                                                                                                                                                                                             | Mandatory   |

#### Optional Fields

| Field         | Description                                                                                                                                                                             | Notes      |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **disclaimer**| - A note regarding limitations or special conditions of the evaluation.                                                                                                               | Optional   |
| **args**      | - Additional key-value pairs passed to evaluator constructors. <br> - Used for evaluator-specific configuration (e.g., thresholds, model configurations, etc.).                     | Optional   |

### 2. Case-Specific Configuration

Each case identifier from the Test Evaluation Configuration must have a corresponding section that details the specific test case.

**Mandatory Fields:**

- **metrics** (list):  
  - A list of evaluator names to be applied to the test case (must match those defined above).

- **evaluations** (list):  
  - Each evaluation item must include:
    - **query** (string, mandatory): The output field key for evaluation (e.g., "patient_information.patient_name").
    - **ground_truth** (string, mandatory): The expected value for the query.

**Optional Fields:**

- **Custom evaluator settings:**  
  - Additional configuration for specific evaluators can be provided using the evaluator's unique name as a key.
- **context** (object):  
  - A mapping used for creating context objects. The key should follow the format "module_path:ClassName" and the value an object with initialization parameters.
- **conversation, scores** (object):  
  - Additional optional details to capture the evaluation process.

### Example Definitive YAML Schema

Below is an annotated YAML snippet illustrating the schema with both mandatory and optional fields:

```yaml
# --- Test Evaluation Configuration ---
evaluation_id:
  description: >
    [MANDATORY] A brief explanation of what this evaluation verifies.
  disclaimer: >
    [OPTIONAL] Any notes on limitations or conditions.
  pipeline:
    class: [MANDATORY] src.pipeline.<ModuleName>.evaluator.<EvaluatorClassName>
    uploaded_files: [MANDATORY/Conditional] "path/to/documents"  # Adjust based on evaluator requirements
    # Alternatively, use 'case_id' and 'scenario' as needed
  evaluators:
    - type: [MANDATORY] "azure" or "custom"
      name: [MANDATORY] "EvaluatorUniqueName"
      class: [MANDATORY] module_path:EvaluatorClassName
      args: [OPTIONAL]
        # Example: Key-value pairs for evaluator-specific configuration
        threshold: 95.0
  cases:
    - evaluation_id.v0

# --- Case-Specific Configuration ---
evaluation_id.v0:
  metrics: [MANDATORY] [EvaluatorUniqueName, ...]
  # Custom evaluator settings [OPTIONAL]
  EvaluatorUniqueName:
    threshold: 95.0
  evaluations:
    - query: [MANDATORY] "field.key.path"
      ground_truth: [MANDATORY] "expected value"
      # Optional fields:
      context: [OPTIONAL] >
        Additional context if needed.
```

For an example YAML configuration, please refer to the file located at `evals/cases/_yaml.example`.

---

## Pipeline Evaluator Implementation

At the core of the evaluation process is the abstract class `PipelineEvaluator` (located in `src/evals/pipeline.py`). This base class enforces a standard workflow that includes:

1. **Preprocessing:**  
   Loads YAML configurations, instantiates evaluators, and prepares data.  
   _Method to implement: `async def preprocess(self)`_

2. **Run Evaluations:**  
   Processes test cases and triggers the evaluation logic (e.g., via the Azure AI evaluation API).  
   _Method to implement: `async def run_evaluations(self)`_

3. **Post Processing:**  
   Aggregates, processes, and summarizes evaluation results.  
   _Method to implement: `def post_processing(self) -> dict`_

These steps are orchestrated by the **final** method `run_pipeline()`, which must not be overridden. This design guarantees a consistent execution order across all evaluator implementations.

**Model Configuration Handling:**  
The `PipelineEvaluator` class supports clean handling of the `model_config` parameter for evaluators. Within the `_instantiate_evaluators()` method, if an evaluator's constructor expects a `model_config` parameter and it is not provided in the YAML configuration (under `args`), the framework automatically populates `model_config` using environment variables (e.g., `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY`, and `AZURE_OPENAI_DEPLOYMENT`). This approach allows model-specific configurations to be either explicitly defined in the YAML configuration or seamlessly injected during the preprocessing steps.

---

## Contribution Guidelines

Contributions to the framework should adhere to these principles:

- **Configuration vs. Code:**  
  Test cases and evaluation parameters belong in YAML files. Evaluator classes should interpret these configurations and apply corresponding logic, ensuring that changes in testing scenarios do not require code modifications.

- **Implementing Custom Evaluators:**  
  When adding a new custom evaluator, create an evaluator class (typically in your module’s `evaluator.py`) that inherits from `PipelineEvaluator`. Your class must implement:
  - `async def preprocess(self)`
  - `async def run_evaluations(self)`
  - `def post_processing(self) -> dict`
  - Optionally, implement `async def generate_responses(self, **kwargs) -> dict` for dynamic response generation.
  
  **Note:** Do not override the `run_pipeline()` method. It is defined as `final` to enforce the standard three-step process.

- **Best Practices:**  
  Externalizing test cases in YAML follows industry standards (e.g., the Twelve-Factor App methodology) and results in:
  - Improved maintainability.
  - Easier updates and debugging.
  - Enhanced scalability for new evaluation scenarios or dependencies.

---

## Usage

To run the evaluations for specific pipelines, set the necessary environment variables and execute the corresponding evaluator script.

**For the `agenticRag` evaluation pipeline:**

```bash
export AZURE_OPENAI_ENDPOINT="https://foundryinstance12345.openai.azure.com" && \
export AZURE_OPENAI_KEY="<scrubbed>" && \
export AZURE_OPENAI_DEPLOYMENT="gpt-4o" && \
export AZURE_AI_FOUNDRY_CONNECTION_STRING="eastus2.api.azureml.ms;28d2df62-e322-4b25-b581-c43b94bd2607;rg-priorauth-eastus2-hls-autoauth;evaluations" && \
export PYTHONPATH="/Users/marcjimz/Documents/Development/gbb-ai-hls-factory-prior-auth:$PYTHONPATH" && \
python src/pipeline/agenticRag/evaluator.py
```

**For the `clinicalExtractor` evaluation pipeline:**

```bash
export AZURE_OPENAI_ENDPOINT="https://foundryinstance12345.openai.azure.com" && \
export AZURE_OPENAI_KEY="<scrubbed>" && \
export AZURE_OPENAI_DEPLOYMENT="gpt-4o" && \
export AZURE_AI_FOUNDRY_CONNECTION_STRING="eastus2.api.azureml.ms;28d2df62-e322-4b25-b581-c43b94bd2607;rg-priorauth-eastus2-hls-autoauth;evaluations" && \
export PYTHONPATH="/Users/marcjimz/Documents/Development/gbb-ai-hls-factory-prior-auth:$PYTHONPATH" && \
python src/pipeline/clinicalExtractor/evaluator.py
```

**For the `autoDetermination` evaluation pipeline:**

```bash
export AZURE_OPENAI_ENDPOINT="https://aoai-ai-factory-eus-dev.openai.azure.com/" && \
export AZURE_OPENAI_KEY="<scrubbed>" && \
export AZURE_OPENAI_DEPLOYMENT="gpt-4o-standard" && \
export AZURE_AI_FOUNDRY_CONNECTION_STRING="eastus2.api.azureml.ms;28d2df62-e322-4b25-b581-c43b94bd2607;rg-priorauth-eastus2-hls-autoauth;evaluations" && \
export PYTHONPATH="/Users/marcjimz/Documents/Development/gbb-ai-hls-factory-prior-auth:$PYTHONPATH" && \
export AZURE_OPENAI_CHAT_DEPLOYMENT_01="o1-preview" && \
export AZURE_OPENAI_API_VERSION_01="2024-09-01-preview" && \
export AZURE_OPENAI_CHAT_DEPLOYMENT_ID="gpt-4o-standard" && \
python src/pipeline/autoDetermination/evaluator.py
```

Make sure to update the environment variables according to your system configuration and connection details.