# Spec: Blob-Triggered Policy Indexer — Offloading AI Search Skillsets to Azure Functions

> **Status:** Approved — implementing
> **Date:** 2026-02-17
> **Supersedes:** [policy-indexer-function-app.md](policy-indexer-function-app.md)

## Decisions

| # | Question | Decision |
|---|----------|----------|
| Q1 | OCR engine | **Azure Document Intelligence** (`prebuilt-layout`) — richer output, already deployed |
| Q2 | Chunk ID compatibility | **Full re-index** — clean break, we control the ID format going forward |
| Q3 | Blob delete handling | **Skip for now** — low priority for policy documents |
| Q4 | Concurrency/scale | **Flexible design** — configurable concurrency limits, batching params externalized |
| Q5 | HTTP endpoints | **Keep `upload_policies`**; add a **`/api/processing_status`** endpoint with session-based tracking for observability |
| Q6 | Migration strategy | **Big bang** — replace the AI Search skillset/indexer/data-source pipeline entirely |
| Q7 | Query-time vectorizer | **Move to function app** — pre-vectorize queries in the backend/search plugin, remove dependency on AI Search vectorizer calling out to OpenAI |

---

## 1. Problem Statement

The current architecture delegates OCR, text chunking, and embedding generation to **Azure AI Search skillsets** (OcrSkill, SplitSkill, AzureOpenAIEmbeddingSkill). While convenient, this design has critical limitations for **customer private networking scenarios**:

| Limitation | Impact |
|---|---|
| AI Search skillsets make **outbound calls** to Cognitive Services (OCR) and Azure OpenAI (embeddings) | These calls traverse public endpoints or require complex private endpoint + shared private link configurations that are poorly supported or region-limited |
| The AI Search indexer's `GENERATE_NORMALIZED_IMAGE_PER_PAGE` image action and OCR skill pipeline is a **closed system** — no custom retry, logging, or error handling | No observability into skill failures in private network scenarios |
| Shared Private Link resources in AI Search are limited, slow to provision, and have [documented product limitations](https://learn.microsoft.com/en-us/azure/search/search-indexer-howto-access-private) | Near-impossible in many enterprise private networking topologies |
| AI Search skillset calls to Azure OpenAI for embeddings don't support VNet injection | Embeddings generation fails when OpenAI is VNet-restricted |
| CognitiveServicesAccountKey auth is required for OCR (managed identity not fully supported for multi-service AI Services in skillsets) | Key-based auth is often prohibited by customer security policy |

### Goal

**Move all document processing (OCR, chunking, embedding) into the Function App itself**, triggered by blob storage events. The Function App pushes **fully-formed documents** (text + vectors) directly into the Azure AI Search index via the Search SDK — **no skillsets, no indexer, no data source connection** needed on the AI Search side.

This means AI Search becomes a **pure query engine** — it holds the index and vectorizer config for query-time vectorization, nothing else.

---

## 2. Current Architecture (As-Is)

### Data Flow

```
PDF upload → Blob Storage (pre-auth-policies/policies_ocr/)
                    ↓
        AI Search Data Source Connection
                    ↓
        AI Search Indexer (triggers on blob)
                    ↓
        AI Search Skillset:
          ├── OcrSkill (calls Cognitive Services)
          ├── SplitSkill (3000 chars / 500 overlap)
          └── AzureOpenAIEmbeddingSkill (calls Azure OpenAI)
                    ↓
        AI Search Index (ai-policies-index)
            fields: chunk_id, chunk, vector, parent_id, title, parent_path, page_number
```

### AI Search Resources Currently Created

| Resource | Name | Purpose |
|---|---|---|
| Data Source | `ai-policies-blob` | Connects AI Search to `pre-auth-policies` blob container |
| Skillset | `ai-policies-skillset` | OCR → Split → Embed pipeline |
| Indexer | `ai-policies-indexer` | Orchestrates data source → skillset → index |
| Index | `ai-policies-index` | Stores chunks + vectors with semantic config |

### Skillset Chain Detail (from `settings.yaml`)

1. **OcrSkill**: Context `/document/normalized_images/*` — extracts text from page images using Cognitive Services OCR, outputs `text` and `layoutText`
2. **SplitSkill**: Context `/document/normalized_images/*` — splits OCR text into 3000-char pages with 500-char overlap, outputs `pages`
3. **AzureOpenAIEmbeddingSkill**: Context `/document/normalized_images/*/pages/*` — generates embeddings via `text-embedding-3-large` (3072 dims)

### Index Schema

| Field | Type | Key | Searchable | Filterable |
|---|---|---|---|---|
| `chunk_id` | String | ✅ (keyword analyzer) | | ✅ |
| `chunk` | String | | ✅ | |
| `vector` | Collection(Single) | | | |
| `parent_id` | String | | | ✅ |
| `title` | String | | | |
| `parent_path` | String | | | |
| `page_number` | String | | | ✅ |

Vector config: HNSW (m=4, ef_construction=400, ef_search=500), profile `myHnswProfile`, vectorizer `myOpenAI` (for query-time vectorization).

Semantic config: `my-semantic-config` with content field = `chunk`.

### Downstream Consumers

The `AzureSearchPlugin` (Semantic Kernel plugin at `src/agenticai/plugins/plugins_store/retrieval/aisearch.py`) queries the index using:
- Keyword search (simple query)
- Semantic search (vector + semantic reranking via `my-semantic-config`)
- Hybrid search (vector + keyword)

All use `VectorizableTextQuery` which relies on the **index vectorizer** (query-time vectorization). This is unaffected by skillset removal — the vectorizer config on the index stays.

---

## 3. Proposed Architecture (To-Be)

### Data Flow

```
PDF upload → Blob Storage (pre-auth-policies/policies_ocr/)
                    ↓
        Event Grid Subscription (blob created/updated)
                    ↓
        Azure Function (Event Grid trigger)
          ├── Download PDF from blob
          ├── Azure Document Intelligence OCR (prebuilt-layout)
          ├── Text chunking (3000 chars / 500 overlap)
          ├── Azure OpenAI embedding (text-embedding-3-large, 3072 dims)
          └── Push documents to AI Search index via SearchClient.upload_documents()
                    ↓
        AI Search Index (ai-policies-index) — QUERY ONLY
            Same schema, same vectorizer for query-time, same semantic config
```

### What Gets Removed from AI Search

| Resource | Action |
|---|---|
| Data Source (`ai-policies-blob`) | **Delete** — no longer needed |
| Skillset (`ai-policies-skillset`) | **Delete** — processing moves to Function App |
| Indexer (`ai-policies-indexer`) | **Delete** — Function App pushes directly |

### What Stays in AI Search

| Resource | Notes |
|---|---|
| Index (`ai-policies-index`) | Same schema, same fields, same vectorizer for query-time |
| Vectorizer config (`myOpenAI`) | Still needed for query-time `VectorizableTextQuery` |
| Semantic config (`my-semantic-config`) | Still needed for semantic search |

---

## 4. Function App Design

### 4.1 Triggers

| Function | Trigger | Description |
|---|---|---|
| `process_blob` | **Event Grid** (Blob Created) | Primary trigger — processes new/updated PDFs automatically |
| `process_blob_manual` | HTTP POST | Manual trigger — accepts a blob path to (re)process a specific document |
| `reindex_all` | HTTP POST | Reprocesses all blobs in the container — for initial seeding or full rebuild |
| `setup_index` | HTTP POST | Creates/updates the AI Search index (schema only, no skillset/indexer/data source) |
| `upload_policies` | HTTP POST | Upload PDF policy documents to blob storage (triggers processing via Event Grid) |
| `processing_status` | HTTP GET | Returns processing session details — status, errors, timing, chunk counts — by session ID or lists recent sessions |
| `vectorize` | HTTP POST | Pre-vectorizes query text using Azure OpenAI — used by downstream search plugin to avoid AI Search outbound calls |
| `health` | HTTP GET | Health check — validates connectivity to all services |

### 4.2 Core Processing Pipeline (`core/document_processor.py`)

```python
class DocumentProcessor:
    """Processes a single PDF: OCR → chunk → embed → push to index."""

    def process(self, blob_url: str, blob_name: str) -> ProcessingResult:
        # 1. Download PDF bytes from blob storage
        pdf_bytes = self.download_blob(blob_name)

        # 2. OCR via Azure Document Intelligence (prebuilt-layout)
        ocr_result = self.doc_intelligence_client.begin_analyze_document(
            model_id="prebuilt-layout",
            analyze_request=AnalyzeDocumentRequest(bytes_source=pdf_bytes),
            output_content_format="text",
        ).result()

        # 3. Extract per-page text
        pages = self.extract_pages(ocr_result)

        # 4. Chunk each page (3000 chars, 500 overlap)
        chunks = self.chunk_pages(pages)

        # 5. Generate embeddings for each chunk (batched)
        embeddings = self.generate_embeddings([c.text for c in chunks])

        # 6. Build index documents
        documents = self.build_index_documents(
            chunks, embeddings, blob_name, blob_url
        )

        # 7. Push to AI Search index
        self.search_client.upload_documents(documents)

        return ProcessingResult(
            blob_name=blob_name,
            page_count=len(pages),
            chunk_count=len(chunks),
        )
```

### 4.3 Chunking Strategy

Replicate the existing AI Search SplitSkill behavior:

| Parameter | Value | Notes |
|---|---|---|
| `text_split_mode` | `pages` | Character-based splitting |
| `maximum_page_length` | 3000 | Characters per chunk |
| `page_overlap_length` | 500 | Overlap between chunks |

Implementation options:
- **LangChain `RecursiveCharacterTextSplitter`** — well-tested, configurable
- **Custom splitter** — minimal dependencies, exact replication of SplitSkill behavior
- **Semantic Kernel TextChunker** — if already in dependency tree

### 4.4 Embedding Strategy

| Parameter | Value |
|---|---|
| Model | `text-embedding-3-large` |
| Dimensions | 3072 |
| Deployment | `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` env var |
| Batching | Up to 16 texts per API call (Azure OpenAI batch limit) |
| Rate limiting | Exponential backoff with tenacity |

### 4.5 Index Document Format

Each chunk pushed to the index:

```json
{
  "chunk_id": "<base64(blob_path)>_chunk_<N>",
  "chunk": "extracted text content...",
  "vector": [0.123, -0.456, ...],  // 3072-dim float array
  "parent_id": "<base64(blob_path)>",
  "title": "policy-document.pdf",
  "parent_path": "pre-auth-policies/policies_ocr/policy-document.pdf",
  "page_number": "3"
}
```

`chunk_id` generation must match what AI Search would have produced (base64-encoded parent key + sequential chunk index) to maintain compatibility with existing data and queries.

### 4.6 Proposed Directory Structure

```
app/indexer/
  function_app.py                # Function definitions (v2 model)
  host.json
  requirements.txt
  local.settings.json
  Dockerfile
  core/
    __init__.py
    config.py                    # Settings loader (YAML + env vars) — existing
    document_processor.py        # NEW: OCR → chunk → embed → push pipeline
    index_manager.py             # NEW: Index schema creation (from existing pipeline.py)
    chunker.py                   # NEW: Text chunking logic
    embedder.py                  # NEW: Azure OpenAI embedding client with batching
  config/
    settings.yaml                # Updated: remove skillset/indexer/data-source config
```

---

## 5. Event Grid Integration

### 5.1 Event Subscription

| Setting | Value |
|---|---|
| Source | Storage Account (`Microsoft.Storage.StorageAccounts`) |
| Event type | `Microsoft.Storage.BlobCreated` |
| Subject filter (prefix) | `/blobServices/default/containers/pre-auth-policies/blobs/policies_ocr/` |
| Subject filter (suffix) | `.pdf` |
| Endpoint | Function App `process_blob` function |
| Delivery | Event Grid trigger (push, at-least-once) |

### 5.2 Event Grid Trigger Function

```python
@app.function_name("process_blob")
@app.event_grid_trigger(arg_name="event")
def process_blob(event: func.EventGridEvent):
    """Triggered when a PDF is uploaded to the policies blob container."""
    blob_url = event.get_json()["url"]
    blob_name = extract_blob_name(blob_url)

    processor = DocumentProcessor()
    result = processor.process(blob_url, blob_name)
    logger.info("Processed %s: %d chunks indexed", blob_name, result.chunk_count)
```

### 5.3 Handling Updates and Deletes

| Event | Behavior |
|---|---|
| Blob created | Process and upsert all chunks (overwrite existing by `chunk_id`) |
| Blob updated (overwritten) | Same as created — `upload_documents` with `merge_or_upload` |
| Blob deleted | Subscribe to `BlobDeleted` event → delete all chunks with matching `parent_id` |

### 5.4 Idempotency

The Event Grid trigger delivers at-least-once. The pipeline must be idempotent:
- `SearchClient.merge_or_upload_documents()` handles upserts naturally
- OCR + embedding are deterministic for the same input
- Concurrent processing of the same blob is unlikely but harmless (last write wins)

---

## 6. Infrastructure Changes

### 6.1 New Bicep Resources

| Resource | Purpose |
|---|---|
| Event Grid System Topic | On the storage account for blob events |
| Event Grid Subscription | Routes `BlobCreated` + `BlobDeleted` to Function App |
| Role assignment: Storage Blob Data Reader | Function App MI → Storage Account (to download blobs) |
| Role assignment: Cognitive Services User | Function App MI → Document Intelligence (OCR) |

### 6.2 Modified Resources

| Resource | Change |
|---|---|
| `functionapp.bicep` | Already exists — add Event Grid trigger app setting, add Document Intelligence endpoint/key |
| `resources.bicep` | Add Event Grid topic + subscription, add new role assignments |

### 6.3 New App Settings

In addition to existing `indexerAppSettings`:

```bicep
{ name: 'AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT', value: docIntelligence.outputs.aiServicesEndpoint }
{ name: 'AZURE_DOCUMENT_INTELLIGENCE_KEY', value: docIntelligence.outputs.aiServicesKey }
```

### 6.4 Removed Logic (from `pipeline.py`)

| Method | Disposition |
|---|---|
| `create_data_source()` | **Remove** — no longer needed |
| `create_skillset()` | **Remove** — processing is in-app |
| `create_indexer()` | **Remove** — no server-side indexer |
| `run_indexer()` | **Remove** — replaced by event-driven processing |
| `setup_all()` | **Simplify** — only calls `create_index()` |

---

## 7. Private Networking Benefits

After this change, the network topology becomes:

```
                          ┌──────────────────────┐
                          │   VNet / Private      │
                          │   Endpoints Zone      │
                          │                       │
  Blob Storage ◄──PE──── │  Function App (VNet   │ ────PE──► Azure OpenAI
  (blob events)           │  integrated)          │           (embeddings)
                          │                       │
  AI Search    ◄──PE──── │  Processes docs       │ ────PE──► Doc Intelligence
  (push index)            │  entirely in-VNet     │           (OCR)
                          │                       │
                          └──────────────────────┘
```

- **All outbound calls** (to OpenAI, Doc Intelligence, AI Search, Storage) go through **private endpoints** controlled by the Function App's VNet integration
- **No shared private links** needed on AI Search (it's not calling out to anything)
- **AI Search** only serves queries — no outbound networking requirements
- Function App VNet integration is a standard, well-supported feature

---

## 8. Resolved Design Decisions

All clarifying questions have been resolved. See the **Decisions** table at the top of this document.

Key implementation notes from the decisions:

- **OCR:** Use `AzureDocumentIntelligenceManager` (existing in `src/documentintelligence/`) with `prebuilt-layout` model
- **Chunk IDs:** Generate our own deterministic scheme (`<sha256(blob_path)>_chunk_<N>`), accept full re-index on cutover
- **No delete handling** for now — can be added later via `BlobDeleted` subscription
- **Concurrency:** Externalize batch sizes, max concurrent requests, and rate limits to `settings.yaml` and env vars
- **Session tracking:** Every processing run (per-blob) gets a `session_id`. Sessions are tracked in-memory with an option to persist to blob storage. The `/api/processing_status` endpoint returns session details including per-step timing, errors, chunk counts, and blob metadata
- **Query vectorization:** Add `/api/vectorize` endpoint; update `AzureSearchPlugin` to call this (or embed locally) instead of using `VectorizableTextQuery`. This removes the last AI Search outbound dependency on OpenAI

---

## 9. Migration Checklist

### Phase 1: Core Processing Logic
- [ ] Create `core/document_processor.py` — OCR → chunk → embed → push pipeline
- [ ] Create `core/chunker.py` — text splitting matching SplitSkill params
- [ ] Create `core/embedder.py` — Azure OpenAI batched embedding with retry
- [ ] Create `core/index_manager.py` — index schema management (extract from `pipeline.py`)
- [ ] Unit tests for chunker, embedder, document processor

### Phase 2: Function App Triggers
- [ ] Add Event Grid trigger function (`process_blob`)
- [ ] Add `BlobDeleted` handler (if Q3 answer is yes)
- [ ] Add `reindex_all` HTTP endpoint
- [ ] Simplify `setup_index` to index-only (no skillset/indexer/data source)
- [ ] Update `health` to check Document Intelligence connectivity
- [ ] Keep or remove `upload_policies` (based on Q5)

### Phase 3: Infrastructure
- [ ] Add Event Grid System Topic to Bicep
- [ ] Add Event Grid Subscription to Bicep
- [ ] Add Document Intelligence app settings to Function App
- [ ] Add role assignments (Cognitive Services User for Doc Intelligence)
- [ ] Update `host.json` for Event Grid configuration

### Phase 4: Cleanup
- [ ] Remove `create_data_source()`, `create_skillset()`, `create_indexer()`, `run_indexer()` from `pipeline.py`
- [ ] Remove `runner.py` (IndexerRunner — no longer needed)
- [ ] Remove AI Search data source, skillset, indexer via a cleanup script or manual deletion
- [ ] Update notebooks to reflect new architecture
- [ ] Update existing spec doc

### Phase 5: Validation
- [ ] Process a single PDF end-to-end via blob upload → Event Grid → Function → index
- [ ] Validate index documents match expected schema
- [ ] Validate downstream agentic RAG queries return same quality results
- [ ] Test delete flow (if implemented)
- [ ] Test `reindex_all` for full rebuild
- [ ] Load test with concurrent PDF uploads
- [ ] Verify private endpoint connectivity for all outbound calls

---

## 10. Dependencies & Packages

New Python packages needed in `app/indexer/requirements.txt`:

```
azure-ai-documentintelligence>=1.0.0    # OCR via Document Intelligence
azure-search-documents>=11.6.0          # Push documents to index
azure-identity>=1.19.0                  # Managed Identity auth
azure-storage-blob>=12.24.0             # Download blobs
openai>=1.60.0                          # Embedding generation
tenacity>=9.0.0                         # Retry logic
```

Packages **no longer needed** for the indexer path (but may stay for backward compat):
- AI Search skillset model classes (`OcrSkill`, `SplitSkill`, `AzureOpenAIEmbeddingSkill`, `SearchIndexer`, `SearchIndexerSkillset`, `SearchIndexerDataSourceConnection`, etc.)

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Chunk ID format mismatch breaking existing queries | Medium | Medium | Full re-index on cutover; `chunk_id` is not typically used in queries |
| Document Intelligence OCR quality differs from Cognitive Services OCR | Low | Medium | DI `prebuilt-layout` is generally superior; validate with existing test PDFs |
| Azure OpenAI rate limiting during bulk reindex | Medium | Medium | Implement batching + exponential backoff; consider provisioned throughput |
| Event Grid delivery failure / duplicate processing | Low | Low | Pipeline is idempotent; Event Grid has built-in retry |
| Increased Function App execution time for large PDFs | Medium | Low | Consumption plan has 10-min timeout; consider App Service plan if PDFs are very large |
