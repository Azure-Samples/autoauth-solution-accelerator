# Changelog

This file meticulously documents all noteworthy changes made to this project.

> **Format Adherence**: This changelog is structured based on the principles outlined in [Keep a Changelog](https://keepachangelog.com/en/1.0.0). To comprehend the formatting and categorization of changes, readers are encouraged to familiarize themselves with this standard.

> **Versioning Protocol**: The project strictly adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (SemVer). SemVer is a versioning scheme for software that aims to convey meaning about the underlying changes with each new release. For details on the version numbering convention, please refer to the [official SemVer specification](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-12-17

### Added
- ✔️ **Core Modules**: Implemented the core modules necessary for the basic functionality of the project. These modules include user authentication, database connection, and API endpoints.
- ✔️ **Documentation**: Created comprehensive documentation to help new developers get started with the project. This includes setup instructions, coding guidelines, and contribution procedures.
- ✔️ **Initial Tests**: Added initial unit tests to ensure the core functionalities work as expected. This helps in maintaining code quality and reliability as the project evolves.
- ✔️ **Infrastructure Components**: Integrated essential infrastructure components to support the scalability and reliability of the project. This includes setting up CI/CD pipelines, containerization with Docker, and deployment scripts.
- ✔️ **Logging and Monitoring**: Implemented comprehensive logging and monitoring solutions to track application performance and detect issues early. This includes integration with monitoring tools and setting up alerting mechanisms.

## [0.2.0] - 2024-12-28

### Refactoring Code for Microservices
Refactored the code for microservices to follow a decoupled architecture and separate front-end/back-end UI as depicted in the new diagram.

### Key Updates

#### Updated Microservice Architecture
- ✔️ Defined roles for `clinicalExtractor`, `AgenticRag`, and `autoDetermination` microservices.
- ✔️ Ensured that each service operates independently with its own configuration files (`run.py`, `settings.yaml`, `evals.py`) and manages specific stages of the processing flow.

#### Enhanced `AgenticRag` Module
- ✔️ Integrated evaluation using LLM to improve accuracy.
- ✔️ Implemented retry logic for retrieval to enhance reliability.

#### FastAPI Integration
- ✔️ Consolidated the FastAPI layer to serve as the main backend interaction point.
- ✔️ Streamlined the `run()` calls to orchestrate processing across the microservices efficiently.

## [0.3.0] - 2025-01-10

### FastAPI Deployment Strategy

- 🔜 Deployment strategy for FastAPI backend using Azure Kubernetes Service (AKS) or containerized applications.
- 🔜 Finalized deployment of the Streamlit UI integration.

### Streamlit Frontend
- 🔜 Enhanced the Streamlit UI to reflect all stages of the processing flow, providing clear, real-time feedback to users.
- 🔜 Integrated proper HTTP POST request handling for seamless backend communication and dynamic response updates.

### AI Gateway & Infra Layer Updates
- 🔜  Leveraged the AI Gateway (APIM) for secure and efficient routing to Azure OpenAI and other AI services.
- 🔜  Ensured Azure components are used optimally to deliver scalable and robust processing solutions.

### CI/CD Integration
- 🔜 Integrated CI/CD pipelines to streamline the deployment process for both backend and frontend components.
- 🔜 Implemented one-click deployment using Azure Developer CLI (AZD) for faster and automated deployment.

### Security Enhancements
- 🔜 Improved security through managed secrets and better access control mechanisms to ensure a secure development and production environment.

## [0.4.0] - 2025-01-16

### Enhanced Evaluation Metrics
- 🔜 Improved evaluation processes by incorporating clear, stage-specific metrics for monitoring and assessment.

### OCR and Extraction Reliability
- 🔜 Enhanced document extraction methods to improve the reliability of OCR and information retrieval processes.

## [Unreleased]

### Added
- ✔️ Agentic runtime behind a runner factory (`AUTOAUTH_RUNNER=legacy|agents|agents-af`; default `legacy`). There are policy, criteria, and determination agents on a typed `CaseState` (`src/agents/`), with optional Microsoft Agent Framework binding (`requirements-agents.txt`).
- ✔️ Evaluator adapters (`src/evals/adapters/`). Legacy-signature runners plus `TraceToEvaluation` keep the existing evaluators and YAML cases as the source of truth.
- ✔️ Data-freshness indicators for policy, clinical evidence, provider affiliation, and member eligibility, shown as badges on the Payor page. They are advisory only and never change the decision.
- ✔️ `progress.py` decouples the PA pipeline from Streamlit (`progress_callback`).
- ✔️ Offline unit tests (`tests/agents`, `tests/adapters`) that use fake clients, with no Azure calls.
- ✔️ Design doc: `docs/architecture/agentic-2026.md`, with a clickable wireframe in `docs/architecture/wireframes/agentic-2026.html`.
- ✔️ Reviewer UI (React + Fluent UI v9, `app/frontend/web/`) with these pages: reviewer queue, case workspace with citations and field-level review, agent trace, provider portal with SSE progress, and quality. Reviewer corrections export as eval-case YAML.
- ✔️ Offline reviewer API (`app/backend/api/`, `uvicorn app.backend.api.app:app`) on fictional demo data, with tests in `tests/api`. Set `AUTOAUTH_REVIEWER_DEMO=1` to mount it on the main backend.
