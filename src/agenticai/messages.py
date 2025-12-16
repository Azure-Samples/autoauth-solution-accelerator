# Copyright (c) Microsoft. All rights reserved.
"""Typed message contracts for Prior Authorization workflow communication.

These dataclasses define the messages passed between executors in the PA workflow.
They serve as the contract for inter-executor communication.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PAProcessingRequest:
    """Initial request to process a prior authorization.

    This is the input message type for the workflow, which DevUI will use
    to generate an input form.
    """

    session_id: str
    """Unique session identifier for this PA request."""

    clinical_text: str
    """Clinical notes or document text to process."""

    procedure_codes: list[str] = field(default_factory=list)
    """List of CPT/HCPCS procedure codes."""

    diagnosis_codes: list[str] = field(default_factory=list)
    """List of ICD-10 diagnosis codes."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata for the request."""


@dataclass
class ExtractionResult:
    """Result from clinical data extraction.

    Contains structured patient, physician, and clinical information
    extracted from the input documents.
    """

    session_id: str
    """Session identifier linking to the original request."""

    patient_data: dict[str, Any] = field(default_factory=dict)
    """Extracted patient demographics and identifiers."""

    physician_data: dict[str, Any] = field(default_factory=dict)
    """Extracted physician/provider information."""

    clinical_data: dict[str, Any] = field(default_factory=dict)
    """Extracted clinical information (diagnoses, procedures, etc.)."""

    raw_text: str = ""
    """Original text that was processed."""


@dataclass
class PolicyQueryRequest:
    """Request to search for relevant medical policies.

    Sent from extraction to the RAG component.
    """

    session_id: str
    """Session identifier."""

    clinical_data: dict[str, Any] = field(default_factory=dict)
    """Clinical context for policy search."""

    query_text: str = ""
    """Natural language query for policy retrieval."""

    procedure_codes: list[str] = field(default_factory=list)
    """Procedure codes to match against policies."""

    diagnosis_codes: list[str] = field(default_factory=list)
    """Diagnosis codes to match against policies."""


@dataclass
class PolicyRetrievalResult:
    """Result from policy retrieval with relevance evaluation.

    Contains matched policies and evaluation metrics.
    """

    session_id: str
    """Session identifier."""

    relevant_policies: list[dict[str, Any]] = field(default_factory=list)
    """List of relevant policy documents with citations."""

    evaluation_score: float = 0.0
    """Overall relevance score (0.0 to 1.0)."""

    reasoning: str = ""
    """Explanation of why these policies are relevant."""

    query_expansions: list[str] = field(default_factory=list)
    """Query variations used during retrieval."""


@dataclass
class DeterminationRequest:
    """Request for PA determination decision.

    Combines clinical data and policies for final decision.
    """

    session_id: str
    """Session identifier."""

    clinical_data: dict[str, Any] = field(default_factory=dict)
    """Extracted clinical information."""

    relevant_policies: list[dict[str, Any]] = field(default_factory=list)
    """Matched policy documents."""

    patient_info: dict[str, Any] = field(default_factory=dict)
    """Patient demographic information."""


@dataclass
class DeterminationResult:
    """Final PA determination result.

    This is the output message type for the workflow.
    """

    session_id: str
    """Session identifier."""

    decision: str = "pending_review"
    """Decision outcome: 'approved', 'denied', or 'pending_review'."""

    reasoning: str = ""
    """Detailed explanation of the decision."""

    confidence_score: float = 0.0
    """Confidence in the decision (0.0 to 1.0)."""

    supporting_evidence: list[str] = field(default_factory=list)
    """List of policy citations and clinical evidence."""

    requires_human_review: bool = False
    """Flag indicating if human review is recommended."""
