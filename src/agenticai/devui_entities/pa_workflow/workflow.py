# Copyright (c) Microsoft. All rights reserved.
"""Prior Authorization Workflow for DevUI.

This is the workflow module that DevUI will discover and load.
It provides a complete PA processing pipeline with mock implementations
for easy testing without Azure dependencies.

Input Schema (PAProcessingRequest):
    - session_id: str - Unique session identifier
    - clinical_text: str - Clinical notes or document text to process
    - procedure_codes: list[str] - CPT/HCPCS procedure codes (optional)
    - diagnosis_codes: list[str] - ICD-10 diagnosis codes (optional)

Output Schema (DeterminationResult):
    - session_id: str - Session identifier
    - decision: str - "approved", "denied", or "pending_review"
    - reasoning: str - Explanation of the decision
    - confidence_score: float - Confidence in decision (0-1)
    - supporting_evidence: list[str] - Policy citations
    - requires_human_review: bool - If human review is needed

Example Input:
    {
        "session_id": "test-001",
        "clinical_text": "65-year-old male with severe osteoarthritis of the right knee...",
        "procedure_codes": ["27447"],
        "diagnosis_codes": ["M17.11"]
    }
"""

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, Workflow, handler
from typing_extensions import Never

logger = logging.getLogger(__name__)


# ============================================================================
# Message Contracts (inline for DevUI self-contained entity)
# ============================================================================


@dataclass
class PAProcessingRequest:
    """Initial request to process a prior authorization."""

    session_id: str
    clinical_text: str
    procedure_codes: list[str] = field(default_factory=list)
    diagnosis_codes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Result from clinical data extraction."""

    session_id: str
    patient_data: dict[str, Any] = field(default_factory=dict)
    physician_data: dict[str, Any] = field(default_factory=dict)
    clinical_data: dict[str, Any] = field(default_factory=dict)
    raw_text: str = ""


@dataclass
class PolicyRetrievalResult:
    """Result from policy retrieval."""

    session_id: str
    relevant_policies: list[dict[str, Any]] = field(default_factory=list)
    evaluation_score: float = 0.0
    reasoning: str = ""
    query_expansions: list[str] = field(default_factory=list)


@dataclass
class DeterminationResult:
    """Final PA determination result."""

    session_id: str
    decision: str = "pending_review"
    reasoning: str = ""
    confidence_score: float = 0.0
    supporting_evidence: list[str] = field(default_factory=list)
    requires_human_review: bool = False


# ============================================================================
# Executors
# ============================================================================


class ClinicalExtractorExecutor(Executor):
    """Extracts clinical data from PA request documents."""

    def __init__(self, id: str = "clinical_extractor"):
        super().__init__(id=id)

    @handler
    async def extract(
        self,
        request: PAProcessingRequest,
        ctx: WorkflowContext[ExtractionResult],
    ) -> None:
        """Extract clinical data from the PA request."""
        logger.info(f"[{self.id}] Extracting clinical data for session: {request.session_id}")

        # Mock extraction - in production, this calls the real extractor
        patient_data = {
            "name": "John Doe",
            "dob": "1985-03-15",
            "member_id": f"MBR-{request.session_id[:8] if len(request.session_id) >= 8 else request.session_id}",
            "gender": "Male",
        }

        physician_data = {
            "name": "Dr. Jane Smith",
            "npi": "1234567890",
            "specialty": "Orthopedics",
        }

        clinical_data = {
            "diagnoses": request.diagnosis_codes or ["M17.11"],
            "procedures": request.procedure_codes or ["27447"],
            "clinical_notes": request.clinical_text[:500] if request.clinical_text else "",
        }

        result = ExtractionResult(
            session_id=request.session_id,
            patient_data=patient_data,
            physician_data=physician_data,
            clinical_data=clinical_data,
            raw_text=request.clinical_text,
        )

        logger.info(f"[{self.id}] Extraction complete: {patient_data.get('name')}")
        await ctx.send_message(result)


class AgenticRAGExecutor(Executor):
    """Retrieves and evaluates relevant policies."""

    def __init__(self, id: str = "agentic_rag"):
        super().__init__(id=id)

    @handler
    async def retrieve_policies(
        self,
        extraction: ExtractionResult,
        ctx: WorkflowContext[PolicyRetrievalResult],
    ) -> None:
        """Retrieve relevant policies based on clinical data."""
        logger.info(f"[{self.id}] Retrieving policies for session: {extraction.session_id}")

        diagnoses = extraction.clinical_data.get("diagnoses", [])
        procedures = extraction.clinical_data.get("procedures", [])

        # Mock policy retrieval
        relevant_policies = [
            {
                "policy_id": "POL-001",
                "title": "Total Knee Arthroplasty Medical Policy",
                "section": "Coverage Criteria",
                "content": (
                    "Total knee arthroplasty is considered medically necessary when: "
                    "1) Conservative treatment has failed for at least 3 months, "
                    "2) Radiographic evidence shows advanced joint disease, "
                    "3) Significant functional impairment is documented."
                ),
                "relevance_score": 0.92,
            },
            {
                "policy_id": "POL-002",
                "title": "Prior Authorization Requirements",
                "section": "Documentation",
                "content": (
                    "Required documentation includes: operative report, "
                    "imaging studies, conservative treatment history, "
                    "and functional assessment scores."
                ),
                "relevance_score": 0.87,
            },
        ]

        # Calculate evaluation score based on clinical context
        # Higher score if both diagnoses and procedures are specified
        base_score = 0.75
        if diagnoses:
            base_score += 0.10
        if procedures:
            base_score += 0.10
        if extraction.raw_text and len(extraction.raw_text) > 100:
            base_score += 0.05

        result = PolicyRetrievalResult(
            session_id=extraction.session_id,
            relevant_policies=relevant_policies,
            evaluation_score=min(base_score, 1.0),
            reasoning=(
                f"Found {len(relevant_policies)} relevant policies for "
                f"diagnoses {diagnoses} and procedures {procedures}."
            ),
            query_expansions=[
                f"knee replacement for {diagnoses[0] if diagnoses else 'osteoarthritis'}",
                f"medical necessity {procedures[0] if procedures else '27447'}",
            ],
        )

        logger.info(f"[{self.id}] Retrieved {len(relevant_policies)} policies, score: {result.evaluation_score:.2f}")
        await ctx.send_message(result)


class DeterminationExecutor(Executor):
    """Generates final PA determination."""

    def __init__(self, confidence_threshold: float = 0.85, id: str = "determination"):
        super().__init__(id=id)
        self._threshold = confidence_threshold

    @handler
    async def determine(
        self,
        retrieval: PolicyRetrievalResult,
        ctx: WorkflowContext[Never, DeterminationResult],
    ) -> None:
        """Generate final PA determination based on policy evaluation."""
        logger.info(f"[{self.id}] Generating determination for session: {retrieval.session_id}")

        score = retrieval.evaluation_score

        if score >= self._threshold:
            decision = "approved"
            confidence = score
            reasoning = (
                f"✅ Prior Authorization APPROVED.\n\n"
                f"Policy evaluation score ({score:.2%}) meets approval threshold ({self._threshold:.0%}).\n\n"
                f"Analysis: {retrieval.reasoning}\n\n"
                f"Clinical documentation supports medical necessity criteria."
            )
            requires_review = False
        elif score >= 0.6:
            decision = "pending_review"
            confidence = score
            reasoning = (
                f"⚠️ HUMAN REVIEW REQUIRED.\n\n"
                f"Policy evaluation score ({score:.2%}) is below auto-approval threshold.\n\n"
                f"Analysis: {retrieval.reasoning}\n\n"
                f"Additional documentation may be needed."
            )
            requires_review = True
        else:
            decision = "denied"
            confidence = 1.0 - score
            reasoning = (
                f"❌ Prior Authorization DENIED.\n\n"
                f"Policy evaluation score ({score:.2%}) indicates insufficient evidence.\n\n"
                f"Analysis: {retrieval.reasoning}\n\n"
                f"Clinical documentation does not meet medical necessity criteria."
            )
            requires_review = False

        supporting_evidence = [
            f"📋 {p.get('title', 'Policy')} - {p.get('section', 'General')}"
            for p in retrieval.relevant_policies
        ]

        result = DeterminationResult(
            session_id=retrieval.session_id,
            decision=decision,
            reasoning=reasoning,
            confidence_score=confidence,
            supporting_evidence=supporting_evidence,
            requires_human_review=requires_review,
        )

        logger.info(f"[{self.id}] Decision: {decision} (confidence: {confidence:.2%})")
        await ctx.yield_output(result)


# ============================================================================
# Workflow Definition
# ============================================================================


def create_workflow() -> "Workflow":
    """Create the PA processing workflow."""
    clinical_extractor = ClinicalExtractorExecutor(id="clinical_extractor")
    agentic_rag = AgenticRAGExecutor(id="agentic_rag")
    determination = DeterminationExecutor(confidence_threshold=0.85, id="determination")

    return (
        WorkflowBuilder(
            name="Prior Authorization Workflow",
            description=(
                "End-to-end Prior Authorization processing pipeline. "
                "Extracts clinical data from documents, retrieves relevant insurance policies, "
                "and generates PA determination decisions (approve/deny/review)."
            ),
        )
        .set_start_executor(clinical_extractor)
        .add_edge(clinical_extractor, agentic_rag)
        .add_edge(agentic_rag, determination)
        .build()
    )


# Export workflow for DevUI discovery
workflow = create_workflow()


if __name__ == "__main__":
    """Run the workflow directly with DevUI."""
    from agent_framework.devui import serve

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("Prior Authorization Workflow - DevUI")
    print("=" * 60)
    print()
    print("Starting DevUI at: http://localhost:8080")
    print()
    print("Test Input Example:")
    print('  {"session_id": "test-001",')
    print('   "clinical_text": "65yo male with severe knee osteoarthritis...",')
    print('   "procedure_codes": ["27447"],')
    print('   "diagnosis_codes": ["M17.11"]}')
    print()
    print("=" * 60)

    serve(entities=[workflow], port=8080, auto_open=True)
