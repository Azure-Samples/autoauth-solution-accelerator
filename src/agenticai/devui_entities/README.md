# Agent Framework DevUI Entities

This directory contains entities (workflows and agents) that can be discovered by the Microsoft Agent Framework DevUI.

## Directory Structure

```
devui_entities/
└── pa_workflow/
    ├── __init__.py     # Exports 'workflow' for DevUI discovery
    └── workflow.py     # PA workflow definition
```

## Running with DevUI

### Option 1: In-Memory Registration (Recommended for Development)

```bash
# From the project root
cd src
python serve_devui.py
```

This will:
- Start DevUI at http://localhost:8080
- Auto-open your browser
- Load the PA workflow with mock implementations

### Option 2: Directory Discovery (CLI)

```bash
# Install DevUI if not already installed
pip install agent-framework-devui --pre

# Run DevUI with directory discovery
cd src
devui ./agenticai/devui_entities --port 8080
```

### Option 3: Run Workflow Directly

```bash
cd src/agenticai/devui_entities/pa_workflow
python workflow.py
```

## Testing the Workflow

Once DevUI is running, you can test the PA workflow with this sample input:

```json
{
  "session_id": "test-001",
  "clinical_text": "65-year-old male with severe osteoarthritis of the right knee. Patient has failed conservative treatment including physical therapy, NSAIDs, and corticosteroid injections over 6 months. X-rays show bone-on-bone changes in the medial compartment. Patient reports significant pain and functional limitation. Requesting authorization for total knee arthroplasty.",
  "procedure_codes": ["27447"],
  "diagnosis_codes": ["M17.11"]
}
```

### Expected Output

The workflow will process through three stages:

1. **Clinical Extraction**: Parses patient, physician, and clinical data
2. **Policy Retrieval**: Finds relevant insurance policies
3. **Determination**: Generates approval/denial decision

Output example:
```json
{
  "session_id": "test-001",
  "decision": "approved",
  "reasoning": "✅ Prior Authorization APPROVED...",
  "confidence_score": 0.95,
  "supporting_evidence": ["📋 Total Knee Arthroplasty Medical Policy - Coverage Criteria", ...],
  "requires_human_review": false
}
```

## Workflow Architecture

```
PAProcessingRequest
        │
        ▼
┌─────────────────────┐
│ ClinicalExtractor   │  Extracts patient/physician/clinical data
│   Executor          │  from input text
└─────────────────────┘
        │
        ▼
   ExtractionResult
        │
        ▼
┌─────────────────────┐
│   AgenticRAG        │  Retrieves relevant policies and
│   Executor          │  evaluates relevance
└─────────────────────┘
        │
        ▼
  PolicyRetrievalResult
        │
        ▼
┌─────────────────────┐
│  Determination      │  Generates final PA decision
│   Executor          │  (approve/deny/pending_review)
└─────────────────────┘
        │
        ▼
  DeterminationResult
```

## Decision Thresholds

- **Approved**: Evaluation score ≥ 85%
- **Pending Review**: Evaluation score 60-85%
- **Denied**: Evaluation score < 60%

The evaluation score is calculated based on:
- Presence of diagnosis codes (+10%)
- Presence of procedure codes (+10%)
- Sufficient clinical text (+5%)
- Base relevance score (75%)
