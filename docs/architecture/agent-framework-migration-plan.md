# Prior Authorization Pipeline Migration to Microsoft Agent Framework

## Executive Summary

This document outlines a phased implementation plan for converting the existing Prior Authorization (PA) processing pipelines to Microsoft Agent Framework workflows. The migration is designed to minimize maintenance overhead and complexity while leveraging the Agent Framework's built-in orchestration, observability, and human-in-the-loop capabilities.

**Note**: All patterns in this document are validated against the official [Microsoft Agent Framework samples repository](https://github.com/microsoft/agent-framework/tree/main/python/samples).

---

## Current Architecture Analysis

### Existing Pipeline Components

| Component | File | Purpose | Lines |
|-----------|------|---------|-------|
| `PAProcessingPipeline` | `src/pipeline/paprocessing/run.py` | Main orchestrator for end-to-end PA processing | ~643 |
| `ClinicalDataExtractor` | `src/pipeline/clinicalExtractor/run.py` | NER extraction for patient/physician/clinical info | ~321 |
| `AgenticRAG` | `src/pipeline/agenticRag/run.py` | Query expansion + policy retrieval + evaluation | ~394 |
| `AutoPADeterminator` | `src/pipeline/autoDetermination/run.py` | Generate final PA determination | ~230 |

### Current Flow

```
Upload Files → Extract Images → Clinical NER → Query Expansion → Policy Retrieval → Evaluation → Determination → Store Output
```

---

## Microsoft Agent Framework Key Patterns

Based on [official samples](https://github.com/microsoft/agent-framework/tree/main/python/samples), the following patterns are essential:

### 1. Executor Pattern with `@handler` Decorator

```python
from agent_framework import Executor, WorkflowContext, handler

class ClinicalExtractorExecutor(Executor):
    """Executor wrapping clinical data extraction logic."""
    
    @handler
    async def extract(
        self, 
        request: ExtractionRequest, 
        ctx: WorkflowContext[ExtractionResult]
    ) -> None:
        # Process extraction
        result = await self._extract_clinical_data(request)
        await ctx.send_message(result)
```

### 2. WorkflowBuilder with Factory Registration (Recommended)

```python
from agent_framework import WorkflowBuilder

workflow = (
    WorkflowBuilder()
    .register_executor(lambda: ClinicalExtractorExecutor(id="clinical_extractor"), name="clinical_extractor")
    .register_executor(lambda: AgenticRAGExecutor(id="agentic_rag"), name="agentic_rag")
    .register_agent(create_determination_agent, name="determination_agent")
    .set_start_executor("clinical_extractor")
    .add_edge("clinical_extractor", "agentic_rag")
    .add_edge("agentic_rag", "determination_agent")
    .build()
)
```

### 3. Fan-Out/Fan-In for Parallel Processing

```python
# From official sample: fan_out_fan_in_edges.py
workflow = (
    WorkflowBuilder()
    .register_agent(create_researcher_agent, name="researcher")
    .register_agent(create_marketer_agent, name="marketer")
    .register_agent(create_legal_agent, name="legal")
    .register_executor(lambda: DispatchToExperts(id="dispatcher"), name="dispatcher")
    .register_executor(lambda: AggregateInsights(id="aggregator"), name="aggregator")
    .set_start_executor("dispatcher")
    .add_fan_out_edges("dispatcher", ["researcher", "marketer", "legal"])
    .add_fan_in_edges(["researcher", "marketer", "legal"], "aggregator")
    .build()
)
```

### 4. Switch-Case for Conditional Routing

```python
from agent_framework import Case, Default

workflow = (
    WorkflowBuilder()
    .set_start_executor(router)
    .add_switch_case_edge_group(
        router,
        [
            Case(condition=lambda msg: msg.status == "approved", target=approved_handler),
            Case(condition=lambda msg: msg.status == "denied", target=denied_handler),
            Default(target=review_handler),
        ],
    )
    .build()
)
```

### 5. Human-in-the-Loop with `request_info` and `@response_handler`

```python
from agent_framework import Executor, WorkflowContext, handler, response_handler
from dataclasses import dataclass

@dataclass
class HumanApprovalRequest:
    """Request sent to the human reviewer."""
    prompt: str
    draft: str
    iteration: int = 0

class ReviewGateway(Executor):
    """Routes agent drafts to humans and optionally back for revisions."""
    
    @handler
    async def on_agent_response(
        self, 
        response: AgentExecutorResponse, 
        ctx: WorkflowContext
    ) -> None:
        await ctx.request_info(
            request_data=HumanApprovalRequest(
                prompt="Review the determination. Reply 'approve' or provide feedback.",
                draft=response.agent_run_response.text,
            ),
            response_type=str,
        )
    
    @response_handler
    async def on_human_feedback(
        self,
        original_request: HumanApprovalRequest,
        feedback: str,
        ctx: WorkflowContext[str, str],
    ) -> None:
        if feedback.lower() == "approve":
            await ctx.yield_output(original_request.draft)
        else:
            # Send back for revision
            await ctx.send_message(RevisionRequest(feedback=feedback))
```

### 6. Checkpointing for Workflow Persistence

```python
from agent_framework import FileCheckpointStorage

storage = FileCheckpointStorage(storage_path=Path("./checkpoints"))
workflow = create_workflow(checkpoint_storage=storage)

# Resume from checkpoint
async for event in workflow.run_stream(checkpoint_id=checkpoint_id):
    if isinstance(event, RequestInfoEvent):
        # Handle human-in-the-loop
        pass
```

---

## Phased Implementation Plan

### Phase 1: Foundation Layer (Weeks 1-2)

**Objective**: Create message contracts and wrapper executors around existing components with minimal code changes.

#### 1.1 Install Dependencies

```bash
pip install agent-framework-azure-ai --pre
```

#### 1.2 Define Message Contracts

Create `src/agenticai/messages.py`:

```python
"""Typed message contracts for PA workflow communication."""
from dataclasses import dataclass, field
from typing import Any
from pydantic import BaseModel

@dataclass
class PAProcessingRequest:
    """Initial request to process a prior authorization."""
    session_id: str
    file_urls: list[str]
    user_id: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ExtractionResult:
    """Result from clinical data extraction."""
    session_id: str
    patient_data: dict[str, Any]
    physician_data: dict[str, Any]
    clinical_data: dict[str, Any]
    extracted_images: list[str]

@dataclass
class PolicyQueryRequest:
    """Request to search for relevant policies."""
    session_id: str
    clinical_data: dict[str, Any]
    query_text: str

@dataclass
class PolicyRetrievalResult:
    """Result from policy retrieval with evaluation."""
    session_id: str
    relevant_policies: list[dict[str, Any]]
    evaluation_score: float
    reasoning: str

@dataclass
class DeterminationRequest:
    """Request for PA determination."""
    session_id: str
    clinical_data: dict[str, Any]
    relevant_policies: list[dict[str, Any]]
    patient_info: dict[str, Any]

@dataclass
class DeterminationResult:
    """Final PA determination result."""
    session_id: str
    decision: str  # "approved", "denied", "pending_review"
    reasoning: str
    confidence_score: float
    supporting_evidence: list[str]
```

#### 1.3 Create Wrapper Executors

Create `src/agenticai/executors/clinical_extractor.py`:

```python
"""Executor wrapper for ClinicalDataExtractor."""
from agent_framework import Executor, WorkflowContext, handler

from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.agenticai.messages import PAProcessingRequest, ExtractionResult


class ClinicalExtractorExecutor(Executor):
    """Executor that wraps the existing ClinicalDataExtractor."""
    
    def __init__(self, config: dict, id: str = "clinical_extractor"):
        super().__init__(id=id)
        self._extractor = ClinicalDataExtractor(**config)
    
    @handler
    async def extract(
        self,
        request: PAProcessingRequest,
        ctx: WorkflowContext[ExtractionResult],
    ) -> None:
        """Extract clinical data from uploaded files."""
        # Call existing extraction logic
        result = await self._extractor.run(
            session_id=request.session_id,
            file_urls=request.file_urls,
        )
        
        extraction_result = ExtractionResult(
            session_id=request.session_id,
            patient_data=result.get("patient_data", {}),
            physician_data=result.get("physician_data", {}),
            clinical_data=result.get("clinical_data", {}),
            extracted_images=result.get("images", []),
        )
        
        await ctx.send_message(extraction_result)
```

Create `src/agenticai/executors/agentic_rag.py`:

```python
"""Executor wrapper for AgenticRAG."""
from agent_framework import Executor, WorkflowContext, handler

from src.pipeline.agenticRag.run import AgenticRAG
from src.agenticai.messages import ExtractionResult, PolicyRetrievalResult


class AgenticRAGExecutor(Executor):
    """Executor that wraps the existing AgenticRAG pipeline."""
    
    def __init__(self, config: dict, id: str = "agentic_rag"):
        super().__init__(id=id)
        self._rag = AgenticRAG(**config)
    
    @handler
    async def retrieve_policies(
        self,
        extraction: ExtractionResult,
        ctx: WorkflowContext[PolicyRetrievalResult],
    ) -> None:
        """Query expansion and policy retrieval with evaluation."""
        result = await self._rag.run(
            session_id=extraction.session_id,
            clinical_data=extraction.clinical_data,
        )
        
        retrieval_result = PolicyRetrievalResult(
            session_id=extraction.session_id,
            relevant_policies=result.get("policies", []),
            evaluation_score=result.get("score", 0.0),
            reasoning=result.get("reasoning", ""),
        )
        
        await ctx.send_message(retrieval_result)
```

Create `src/agenticai/executors/determination.py`:

```python
"""Executor wrapper for AutoPADeterminator."""
from agent_framework import Executor, WorkflowContext, handler
from typing_extensions import Never

from src.pipeline.autoDetermination.run import AutoPADeterminator
from src.agenticai.messages import PolicyRetrievalResult, DeterminationResult


class DeterminationExecutor(Executor):
    """Executor that wraps the existing AutoPADeterminator."""
    
    def __init__(self, config: dict, id: str = "determination"):
        super().__init__(id=id)
        self._determinator = AutoPADeterminator(**config)
    
    @handler
    async def determine(
        self,
        retrieval: PolicyRetrievalResult,
        ctx: WorkflowContext[Never, DeterminationResult],
    ) -> None:
        """Generate final PA determination."""
        result = await self._determinator.run(
            session_id=retrieval.session_id,
            policies=retrieval.relevant_policies,
        )
        
        determination = DeterminationResult(
            session_id=retrieval.session_id,
            decision=result.get("decision", "pending_review"),
            reasoning=result.get("reasoning", ""),
            confidence_score=result.get("confidence", 0.0),
            supporting_evidence=result.get("evidence", []),
        )
        
        # yield_output for final workflow result
        await ctx.yield_output(determination)
```

---

### Phase 2: Workflow Composition (Weeks 3-4)

**Objective**: Compose executors into a workflow using WorkflowBuilder.

#### 2.1 Create Main Workflow

Create `src/agenticai/workflows/pa_workflow.py`:

```python
"""Prior Authorization Workflow using Microsoft Agent Framework."""
from pathlib import Path
from typing import Any

from agent_framework import (
    Workflow,
    WorkflowBuilder,
    FileCheckpointStorage,
)

from src.agenticai.executors.clinical_extractor import ClinicalExtractorExecutor
from src.agenticai.executors.agentic_rag import AgenticRAGExecutor
from src.agenticai.executors.determination import DeterminationExecutor


def create_pa_workflow(
    config: dict[str, Any],
    checkpoint_path: Path | None = None,
) -> Workflow:
    """Create the Prior Authorization processing workflow.
    
    Args:
        config: Configuration dict with Azure credentials and settings
        checkpoint_path: Optional path for checkpoint storage
        
    Returns:
        Configured Workflow instance
    """
    checkpoint_storage = None
    if checkpoint_path:
        checkpoint_storage = FileCheckpointStorage(storage_path=checkpoint_path)
    
    workflow = (
        WorkflowBuilder(
            name="PA Processing Workflow",
            description="End-to-end Prior Authorization processing pipeline",
        )
        # Register executors with factory functions for lazy initialization
        .register_executor(
            lambda: ClinicalExtractorExecutor(
                config=config.get("clinical_extractor", {}),
                id="clinical_extractor",
            ),
            name="clinical_extractor",
        )
        .register_executor(
            lambda: AgenticRAGExecutor(
                config=config.get("agentic_rag", {}),
                id="agentic_rag",
            ),
            name="agentic_rag",
        )
        .register_executor(
            lambda: DeterminationExecutor(
                config=config.get("determination", {}),
                id="determination",
            ),
            name="determination",
        )
        # Define workflow topology
        .set_start_executor("clinical_extractor")
        .add_edge("clinical_extractor", "agentic_rag")
        .add_edge("agentic_rag", "determination")
        .build(checkpoint_storage=checkpoint_storage)
    )
    
    return workflow
```

#### 2.2 Create Workflow Runner

Create `src/agenticai/workflows/runner.py`:

```python
"""Workflow runner with streaming and event handling."""
import asyncio
from typing import Any, AsyncIterator

from agent_framework import (
    Workflow,
    WorkflowEvent,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    ExecutorInvokedEvent,
    ExecutorCompletedEvent,
    RequestInfoEvent,
)

from src.agenticai.messages import PAProcessingRequest, DeterminationResult


async def run_pa_workflow(
    workflow: Workflow,
    request: PAProcessingRequest,
) -> DeterminationResult:
    """Run the PA workflow to completion.
    
    Args:
        workflow: The configured workflow instance
        request: The PA processing request
        
    Returns:
        The final determination result
    """
    final_result: DeterminationResult | None = None
    
    async for event in workflow.run_stream(request):
        if isinstance(event, ExecutorInvokedEvent):
            print(f"[{event.executor_id}] Started processing...")
            
        elif isinstance(event, ExecutorCompletedEvent):
            print(f"[{event.executor_id}] Completed")
            
        elif isinstance(event, WorkflowOutputEvent):
            final_result = event.data
            
        elif isinstance(event, WorkflowStatusEvent):
            if event.state == WorkflowRunState.IDLE:
                print("Workflow completed")
    
    if final_result is None:
        raise RuntimeError("Workflow completed without producing a result")
    
    return final_result


async def run_pa_workflow_streaming(
    workflow: Workflow,
    request: PAProcessingRequest,
) -> AsyncIterator[WorkflowEvent]:
    """Run the PA workflow with streaming events.
    
    Args:
        workflow: The configured workflow instance
        request: The PA processing request
        
    Yields:
        Workflow events as they occur
    """
    async for event in workflow.run_stream(request):
        yield event
```

---

### Phase 3: Human-in-the-Loop Integration (Weeks 5-6)

**Objective**: Add human review capabilities for high-stakes determinations.

#### 3.1 Create Review Gateway Executor

Create `src/agenticai/executors/review_gateway.py`:

```python
"""Human-in-the-loop review gateway executor."""
from dataclasses import dataclass
from typing import Any

from agent_framework import (
    Executor,
    WorkflowContext,
    handler,
    response_handler,
)

from src.agenticai.messages import DeterminationResult


@dataclass
class HumanReviewRequest:
    """Request for human review of a PA determination."""
    session_id: str
    prompt: str
    determination: DeterminationResult
    clinical_summary: str


class ReviewGatewayExecutor(Executor):
    """Routes determinations to human reviewers when needed."""
    
    def __init__(
        self,
        confidence_threshold: float = 0.85,
        id: str = "review_gateway",
    ):
        super().__init__(id=id)
        self._confidence_threshold = confidence_threshold
    
    @handler
    async def evaluate_determination(
        self,
        result: DeterminationResult,
        ctx: WorkflowContext[DeterminationResult, DeterminationResult],
    ) -> None:
        """Evaluate if human review is needed."""
        needs_review = (
            result.confidence_score < self._confidence_threshold
            or result.decision == "pending_review"
        )
        
        if needs_review:
            # Request human review
            await ctx.request_info(
                request_data=HumanReviewRequest(
                    session_id=result.session_id,
                    prompt=(
                        f"Review required for PA determination.\n"
                        f"Decision: {result.decision}\n"
                        f"Confidence: {result.confidence_score:.2%}\n"
                        f"Reasoning: {result.reasoning}\n\n"
                        "Reply 'approve', 'deny', or provide feedback for revision."
                    ),
                    determination=result,
                    clinical_summary=result.reasoning,
                ),
                response_type=str,
            )
        else:
            # Auto-approve high-confidence determinations
            await ctx.yield_output(result)
    
    @response_handler
    async def on_human_feedback(
        self,
        original_request: HumanReviewRequest,
        feedback: str,
        ctx: WorkflowContext[DeterminationResult, DeterminationResult],
    ) -> None:
        """Process human reviewer feedback."""
        reply = feedback.strip().lower()
        determination = original_request.determination
        
        if reply == "approve":
            await ctx.yield_output(determination)
        elif reply == "deny":
            updated = DeterminationResult(
                session_id=determination.session_id,
                decision="denied",
                reasoning=f"Denied by human reviewer. Original: {determination.reasoning}",
                confidence_score=1.0,  # Human decision = full confidence
                supporting_evidence=determination.supporting_evidence,
            )
            await ctx.yield_output(updated)
        else:
            # Feedback requires revision - send back to determination
            revised = DeterminationResult(
                session_id=determination.session_id,
                decision="pending_review",
                reasoning=f"Revision requested: {feedback}. Original: {determination.reasoning}",
                confidence_score=0.0,
                supporting_evidence=determination.supporting_evidence,
            )
            await ctx.send_message(revised)
```

#### 3.2 Update Workflow with Review Gateway

```python
def create_pa_workflow_with_review(
    config: dict[str, Any],
    checkpoint_path: Path | None = None,
    confidence_threshold: float = 0.85,
) -> Workflow:
    """Create PA workflow with human-in-the-loop review."""
    checkpoint_storage = None
    if checkpoint_path:
        checkpoint_storage = FileCheckpointStorage(storage_path=checkpoint_path)
    
    workflow = (
        WorkflowBuilder(
            name="PA Processing Workflow with Review",
            description="PA processing with human-in-the-loop for low-confidence cases",
        )
        .register_executor(
            lambda: ClinicalExtractorExecutor(config=config.get("clinical_extractor", {})),
            name="clinical_extractor",
        )
        .register_executor(
            lambda: AgenticRAGExecutor(config=config.get("agentic_rag", {})),
            name="agentic_rag",
        )
        .register_executor(
            lambda: DeterminationExecutor(config=config.get("determination", {})),
            name="determination",
        )
        .register_executor(
            lambda: ReviewGatewayExecutor(confidence_threshold=confidence_threshold),
            name="review_gateway",
        )
        .set_start_executor("clinical_extractor")
        .add_edge("clinical_extractor", "agentic_rag")
        .add_edge("agentic_rag", "determination")
        .add_edge("determination", "review_gateway")
        .build(checkpoint_storage=checkpoint_storage)
    )
    
    return workflow
```

---

### Phase 4: Convert to Native Agents with Tools (Weeks 7-9)

**Objective**: Replace executor wrappers with native Agent Framework agents using tools.

#### 4.1 Create Agent Tools

Create `src/agenticai/tools/clinical_tools.py`:

```python
"""Clinical extraction tools for agents."""
from agent_framework import ai_function
from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    """Patient information extracted from documents."""
    name: str = Field(description="Patient full name")
    dob: str = Field(description="Date of birth")
    member_id: str = Field(description="Insurance member ID")
    diagnosis: list[str] = Field(description="List of diagnoses")


@ai_function(name="extract_patient_info")
async def extract_patient_info(
    document_text: str,
) -> PatientInfo:
    """Extract patient information from clinical document text.
    
    Args:
        document_text: The raw text from the clinical document
        
    Returns:
        Structured patient information
    """
    # Implementation using existing extraction logic
    from src.extractors.patient import extract_patient_data
    result = await extract_patient_data(document_text)
    return PatientInfo(**result)


@ai_function(name="search_policies")
async def search_policies(
    diagnosis_codes: list[str],
    procedure_codes: list[str],
) -> list[dict]:
    """Search for relevant medical policies based on diagnosis and procedure codes.
    
    Args:
        diagnosis_codes: List of ICD-10 diagnosis codes
        procedure_codes: List of CPT/HCPCS procedure codes
        
    Returns:
        List of relevant policy documents with citations
    """
    from src.pipeline.agenticRag.run import AgenticRAG
    rag = AgenticRAG()
    return await rag.search_policies(diagnosis_codes, procedure_codes)
```

#### 4.2 Create Determination Agent

Create `src/agenticai/agents/determination_agent.py`:

```python
"""PA Determination Agent using Azure OpenAI."""
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential

from src.agenticai.tools.clinical_tools import search_policies


def create_determination_agent() -> ChatAgent:
    """Create the PA determination agent with tools."""
    credential = DefaultAzureCredential()
    chat_client = AzureOpenAIChatClient(
        credential=credential,
        model_deployment_name="gpt-4o",
    )
    
    agent = chat_client.create_agent(
        name="pa_determinator",
        instructions="""You are a Prior Authorization determination specialist.

Your role is to analyze clinical information and policy documents to make PA decisions.

Guidelines:
1. Always cite specific policy sections that support your decision
2. Explain your reasoning step by step
3. If information is insufficient, request additional details
4. Flag cases that require human review

Output Format:
- Decision: APPROVED / DENIED / PENDING_REVIEW
- Confidence: 0-100%
- Reasoning: Detailed explanation
- Evidence: List of supporting policy citations
""",
        tools=[search_policies],
    )
    
    return agent
```

---

### Phase 5: Advanced Patterns & Rollout (Weeks 10-12)

**Objective**: Implement advanced patterns and gradual production rollout.

#### 5.1 Parallel Policy Analysis (Fan-Out/Fan-In)

```python
from agent_framework import WorkflowBuilder

def create_parallel_analysis_workflow(config: dict) -> Workflow:
    """Create workflow with parallel policy analysis."""
    return (
        WorkflowBuilder(name="PA Parallel Analysis")
        .register_executor(
            lambda: ClinicalExtractorExecutor(config=config),
            name="clinical_extractor",
        )
        .register_executor(
            lambda: DispatcherExecutor(),
            name="dispatcher",
        )
        .register_agent(create_medical_necessity_agent, name="medical_necessity")
        .register_agent(create_coverage_verification_agent, name="coverage")
        .register_agent(create_documentation_agent, name="documentation")
        .register_executor(
            lambda: AggregatorExecutor(),
            name="aggregator",
        )
        .register_executor(
            lambda: DeterminationExecutor(config=config),
            name="determination",
        )
        # Sequential: extraction -> dispatch
        .set_start_executor("clinical_extractor")
        .add_edge("clinical_extractor", "dispatcher")
        # Fan-out: dispatch to parallel analyzers
        .add_fan_out_edges("dispatcher", ["medical_necessity", "coverage", "documentation"])
        # Fan-in: collect all analysis results
        .add_fan_in_edges(["medical_necessity", "coverage", "documentation"], "aggregator")
        # Final determination
        .add_edge("aggregator", "determination")
        .build()
    )
```

#### 5.2 Feature Flag Integration

```python
"""Feature flag-based workflow selection."""
from enum import Enum

class WorkflowMode(Enum):
    LEGACY = "legacy"
    HYBRID = "hybrid"  # Agent Framework with legacy components
    NATIVE = "native"  # Full Agent Framework

async def process_pa_request(
    request: PAProcessingRequest,
    mode: WorkflowMode = WorkflowMode.HYBRID,
) -> DeterminationResult:
    """Process PA request with configurable workflow mode."""
    
    if mode == WorkflowMode.LEGACY:
        # Use existing PAProcessingPipeline
        from src.pipeline.paprocessing.run import PAProcessingPipeline
        pipeline = PAProcessingPipeline()
        return await pipeline.run(request)
    
    elif mode == WorkflowMode.HYBRID:
        # Use Agent Framework with wrapper executors
        workflow = create_pa_workflow_with_review(config)
        return await run_pa_workflow(workflow, request)
    
    else:  # NATIVE
        # Use full Agent Framework with native agents
        workflow = create_parallel_analysis_workflow(config)
        return await run_pa_workflow(workflow, request)
```

---

## File Structure After Migration

```
src/
├── agenticai/
│   ├── __init__.py
│   ├── messages.py           # Typed message contracts
│   ├── executors/
│   │   ├── __init__.py
│   │   ├── clinical_extractor.py
│   │   ├── agentic_rag.py
│   │   ├── determination.py
│   │   └── review_gateway.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── determination_agent.py
│   │   └── analysis_agents.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── clinical_tools.py
│   │   └── policy_tools.py
│   └── workflows/
│       ├── __init__.py
│       ├── pa_workflow.py
│       └── runner.py
```

---

## Testing Strategy

### Unit Tests

```python
# tests/agenticai/test_executors.py
import pytest
from src.agenticai.executors.clinical_extractor import ClinicalExtractorExecutor
from src.agenticai.messages import PAProcessingRequest

@pytest.mark.asyncio
async def test_clinical_extractor_executor():
    """Test clinical extractor produces valid extraction result."""
    executor = ClinicalExtractorExecutor(config={})
    # Mock and test...
```

### Integration Tests

```python
# tests/agenticai/test_workflow.py
import pytest
from src.agenticai.workflows.pa_workflow import create_pa_workflow

@pytest.mark.asyncio
async def test_full_workflow():
    """Test complete PA workflow execution."""
    workflow = create_pa_workflow(config={})
    request = PAProcessingRequest(
        session_id="test-123",
        file_urls=["file1.pdf"],
        user_id="user-1",
    )
    
    result = await run_pa_workflow(workflow, request)
    assert result.decision in ["approved", "denied", "pending_review"]
```

---

## Rollout Plan

| Week | Milestone | Success Criteria |
|------|-----------|------------------|
| 1-2 | Foundation Layer | Message contracts defined, wrapper executors created |
| 3-4 | Workflow Composition | End-to-end workflow runs in dev environment |
| 5-6 | Human-in-the-Loop | Review gateway tested with simulated reviewers |
| 7-9 | Native Agents | At least one pipeline converted to native agents |
| 10-11 | Parallel Patterns | Fan-out/fan-in working for policy analysis |
| 12 | Production Rollout | Feature-flagged deployment with 10% traffic |

---

## References

- [Microsoft Agent Framework Python Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples)
- [Workflow Patterns - Fan-Out/Fan-In](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/workflows/parallelism)
- [Human-in-the-Loop Samples](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/workflows/human-in-the-loop)
- [Checkpoint and Persistence](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/workflows/checkpoint)
- [Switch-Case Control Flow](https://github.com/microsoft/agent-framework/tree/main/python/samples/getting_started/workflows/control-flow)
