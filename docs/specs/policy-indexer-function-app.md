# Spec: Policy Indexer Function App

## Overview

Extract the policy indexing and AI Search skill/index creation logic from the current Container App Job (which reuses the **frontend container image**) into a dedicated **Azure Function App**. This provides proper separation of concerns, independent scaling, better operational tooling (monitoring, retries, scheduling), and removes the coupling between the web frontend image and a backend data pipeline.

---

## Current Architecture (As-Is)

### Execution Model
- **Container App Job** (`indexInitializationJob`) with `triggerType: Manual`
- Reuses the **frontend container image** (`frontendImage`)
- Runs: `python /app/src/pipeline/policyIndexer/indexerSetup.py --target '/app'`
- Deployed in the same Container Apps Environment as the frontend

### Source Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| `PolicyIndexingPipeline` | `src/pipeline/policyIndexer/run.py` | Orchestrates all index setup (data source, index, skillset, indexer creation) + document upload |
| `IndexerRunner` | `src/pipeline/policyIndexer/run.py` | Runs the indexer and monitors status with polling |
| `indexerSetup.py` | `src/pipeline/policyIndexer/indexerSetup.py` | CLI entry point — calls pipeline + runner + test search sequentially |
| `settings.yaml` | `src/pipeline/policyIndexer/settings.yaml` | Index schema, skillset config, vector search config, blob container settings |
| Policy PDFs | `utils/data/cases/policies/` (5 PDFs) | Source documents uploaded to blob, then indexed |

### Pipeline Steps (from notebook `01-indexing-policies.ipynb`)

```
1. Upload PDFs → Azure Blob Storage (container: pre-auth-policies, path: policies_ocr/)
2. Create Data Source → Connect AI Search to blob container
3. Create Index → Define fields (chunk, vector, parent_id, title, page_number, etc.)
4. Create Skillset → OCR → Split (3000 chars / 500 overlap) → Embedding (text-embedding-3-large, 3072 dims)
5. Create Indexer → Wire data source → skillset → index
6. Run Indexer → Trigger execution
7. Monitor Status → Poll until success/failure
```

### Current Environment Variables Required

```
AZURE_AI_SEARCH_SERVICE_ENDPOINT
AZURE_AI_SEARCH_ADMIN_KEY
AZURE_STORAGE_CONNECTION_STRING
AZURE_STORAGE_ACCOUNT_NAME
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_KEY
AZURE_OPENAI_EMBEDDING_DEPLOYMENT
AZURE_OPENAI_EMBEDDING_MODEL_NAME  (default: text-embedding-3-large)
AZURE_OPENAI_EMBEDDING_DIMENSIONS  (default: 3072)
AZURE_AI_SERVICES_KEY
```

---

## Proposed Architecture (To-Be)

### Azure Function App: `func-policy-indexer`

A **dedicated Python Azure Function App** (Flex Consumption or App Service plan) with HTTP-triggered and optionally timer-triggered functions.

### Proposed Function Endpoints

| Function | Trigger | Description |
|----------|---------|-------------|
| `setup_index` | HTTP (POST) | Creates/updates data source, index, skillset, and indexer. Idempotent — safe to re-run. |
| `upload_policies` | HTTP (POST) | Accepts PDF files via multipart upload OR triggers upload from blob staging container. Uploads to the landing zone blob path. |
| `run_indexer` | HTTP (POST) | Triggers the AI Search indexer run. Returns immediately with 202 Accepted. |
| `indexer_status` | HTTP (GET) | Returns current indexer status (running, success, error, etc.). |
| `reindex` | HTTP (POST) | Orchestrates full pipeline: setup_index → run_indexer. Convenience endpoint. |
| `reindex_scheduled` | Timer (optional) | Cron-based trigger to re-run the indexer on a schedule (e.g., nightly). |
| `health` | HTTP (GET) | Health check — validates connectivity to AI Search, Blob Storage, OpenAI. |

### Proposed Directory Structure

```
app/
  indexer/                          # New Function App
    host.json
    local.settings.json
    requirements.txt
    Dockerfile                      # If containerized deployment preferred
    function_app.py                 # Main function definitions (v2 programming model)
    core/
      pipeline.py                   # Refactored PolicyIndexingPipeline
      runner.py                     # Refactored IndexerRunner
      config.py                     # Settings loader (YAML + env vars)
      models.py                     # Request/response models
    config/
      settings.yaml                 # Migrated from src/pipeline/policyIndexer/settings.yaml
```

---

## Components to Extract / Refactor

### 1. `PolicyIndexingPipeline` → `core/pipeline.py`

**What moves:**
- `__init__()` — Configuration loading (YAML + env vars)
- `upload_documents()` — PDF upload to blob storage
- `create_data_source()` — AI Search data source connection
- `create_index()` — Search index with vector/semantic config
- `create_skillset()` — OCR + split + embedding skillset
- `create_indexer()` — Indexer wiring
- `run_indexer()` — Trigger indexer run
- `indexing()` — Full orchestration

**Refactoring needed:**
- Remove `os.chdir()` / working directory logic (not needed in Functions)
- Make `settings.yaml` path configurable via env var (e.g., `INDEXER_CONFIG_PATH`)
- Replace `local_path` parameter in `upload_documents()` with blob-to-blob copy or HTTP file upload
- Add proper return types (not just logging) for function responses
- Replace `dotenv.load_dotenv()` with Function App application settings
- Switch from key-based auth to **Managed Identity** where possible (AI Search, Blob, OpenAI)

### 2. `IndexerRunner` → `core/runner.py`

**What moves:**
- `run_indexer()` — Trigger execution
- `check_indexer_status()` — Status polling
- `monitor_indexer_status()` — Polling loop

**Refactoring needed:**
- `monitor_indexer_status()` should NOT be a blocking loop in a Function. Instead:
  - `run_indexer` returns 202 with a status check URL
  - `indexer_status` is a separate GET endpoint
  - Optionally use **Durable Functions** for orchestration with async polling

### 3. `settings.yaml` → `config/settings.yaml`

**What moves:** The entire YAML config file, unchanged.

**Refactoring needed:**
- Override `index_name`, `container_name`, etc. via env vars/app settings so different environments (dev/staging/prod) can use different indexes
- Consider making the YAML a baseline with env var overrides

### 4. Policy PDFs — Upload Strategy

**Current:** PDFs live in `utils/data/cases/policies/` in the repo and are uploaded from local disk.

**Options for Function App:**

| Option | Description | Recommended |
|--------|-------------|-------------|
| A: Blob event trigger | PDFs dropped into a staging blob container trigger the Function | Yes — for ongoing operations |
| B: HTTP upload | POST PDFs to the `upload_policies` endpoint | Yes — for manual/ad-hoc uploads |
| C: Bundle in image | Bake PDFs into the Function App container (like current approach) | No — tightly couples data to code |
| D: Seed script | Separate one-time script for initial seeding (keep `indexerSetup.py`) | Yes — for initial deployment only |

**Recommendation:** Option A + B for runtime, Option D for initial data seeding during `azd up`.

---

## Infrastructure Changes (Bicep)

### New Resources

| Resource | Module | Purpose |
|----------|--------|---------|
| Azure Function App | `modules/compute/functionapp.bicep` | Hosts the indexer functions |
| App Service Plan (or Flex Consumption) | Part of function app module | Compute for the function |
| Storage Account (Functions) | Reuse existing or new | Required by Azure Functions runtime |

### Resources to Remove

| Resource | Current Definition | Reason |
|----------|-------------------|--------|
| `indexInitializationJob` | Container App Job in `resources.bicep` | Replaced by Function App |
| `jobAppContainer` variable | `resources.bicep` | No longer needed |
| `frontendImage` dependency for job | `resources.bicep` | Function has its own image/package |

### Role Assignments Needed for Function App Managed Identity

| Role | Target Resource | Purpose |
|------|-----------------|---------|
| Storage Blob Data Contributor | Storage Account | Upload/read policy PDFs |
| Search Index Data Contributor | AI Search | Manage indexes |
| Search Service Contributor | AI Search | Manage indexers, skillsets, data sources |
| Cognitive Services OpenAI User | Azure OpenAI | Generate embeddings |
| Cognitive Services User | Multi-account AI Services | OCR processing |

### Env Vars / App Settings for Function App

Same as current `containerEnvArray` but scoped to only what the indexer needs:

```
AZURE_AI_SEARCH_SERVICE_ENDPOINT
AZURE_AI_SEARCH_ADMIN_KEY          # or use MI
AZURE_STORAGE_CONNECTION_STRING     # or use MI
AZURE_STORAGE_ACCOUNT_NAME
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_KEY                    # or use MI
AZURE_OPENAI_EMBEDDING_DEPLOYMENT
AZURE_OPENAI_EMBEDDING_DIMENSIONS
AZURE_AI_SERVICES_KEY               # for OCR skill
AZURE_SEARCH_INDEX_NAME
APPLICATIONINSIGHTS_CONNECTION_STRING
INDEXER_CONFIG_PATH                 # path to settings.yaml in the function app
```

---

## Migration Checklist

### Phase 1: Scaffold Function App
- [ ] Create `app/indexer/` directory structure
- [ ] Set up `function_app.py` with v2 programming model
- [ ] Create `host.json`, `requirements.txt`, `local.settings.json`
- [ ] Migrate `settings.yaml`

### Phase 2: Refactor Core Logic
- [ ] Extract `PolicyIndexingPipeline` → `core/pipeline.py` (remove local filesystem assumptions)
- [ ] Extract `IndexerRunner` → `core/runner.py` (non-blocking status checks)
- [ ] Create `core/config.py` for settings management
- [ ] Add request/response models in `core/models.py`
- [ ] Write function handlers for each endpoint

### Phase 3: Infrastructure
- [ ] Create `modules/compute/functionapp.bicep`
- [ ] Add Function App deployment to `resources.bicep`
- [ ] Add role assignments for Function App managed identity
- [ ] Remove `indexInitializationJob` Container App Job
- [ ] Remove `jobAppContainer` variable
- [ ] Add Function App outputs
- [ ] Update `azure.yaml` with new `indexer` service

### Phase 4: Auth & Security
- [ ] Switch from API keys to Managed Identity for AI Search, OpenAI, Storage where possible
- [ ] Function App auth (function-level keys or EasyAuth for the HTTP endpoints)
- [ ] Remove hardcoded keys from app settings where MI is used

### Phase 5: Operations
- [ ] Add Application Insights integration
- [ ] Add structured logging (replace `print()` statements from `indexerSetup.py`)
- [ ] Add retry policies on function bindings
- [ ] Optional: Add Durable Functions orchestration for long-running reindex
- [ ] Optional: Add timer trigger for scheduled re-indexing

### Phase 6: Validation
- [ ] Test `setup_index` creates all AI Search resources correctly
- [ ] Test `upload_policies` uploads PDFs to correct blob path
- [ ] Test `run_indexer` triggers and completes successfully
- [ ] Test `indexer_status` returns accurate state
- [ ] Test `reindex` end-to-end
- [ ] Verify existing notebook still works for local dev/testing
- [ ] Remove old Container App Job after validation

---

## Key Design Decisions

| Decision | Recommendation | Rationale |
|----------|---------------|-----------|
| Function App plan | Flex Consumption | Cost-efficient, scales to zero, sufficient for periodic indexing |
| Programming model | v2 (decorator-based) | Simpler, modern Python pattern |
| Deployment model | Code deployment (not container) | Simpler CI/CD, no Docker build needed for a Python function |
| Settings management | YAML + App Settings overrides | Maintains existing YAML structure while allowing per-environment config |
| Long-running monitoring | Separate status endpoint (not blocking) | Functions have execution time limits; polling should be client-side |
| Durable Functions | Optional (Phase 5) | Useful if reindex orchestration needs fan-out or long waits |
| Auth model | Managed Identity primary, keys as fallback | Better security posture, aligns with Azure best practices |

---

## Impact on Existing Components

| Component | Impact |
|-----------|--------|
| `01-indexing-policies.ipynb` | **No change** — continues to work for local dev/testing |
| `src/pipeline/policyIndexer/` | **No change** — remains as the shared library; Function App imports from it or gets a copy |
| `app/backend/` | **No change** — backend API is unaffected |
| `app/frontend/` | **No change** — frontend is unaffected |
| Frontend Dockerfile | **Simplified** — no longer needs to bundle `src/pipeline/` code for the job |
| `resources.bicep` | **Modified** — remove Container App Job, add Function App |
| `azure.yaml` | **Modified** — add `indexer` service definition |
