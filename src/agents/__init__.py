"""AutoAuth agents (2026). See docs/architecture/agentic-2026.md.

Importing this package never imports Microsoft Agent Framework; that binding
lives in :mod:`src.agents.af_binding` and is loaded only when requested.
"""

from src.agents.state import (
    CaseState,
    Citation,
    Criterion,
    CriterionAssessment,
    Determination,
    DocumentSet,
    Freshness,
    MissingInformation,
    PolicyMatch,
    ReviewerAction,
)

__all__ = [
    "CaseState",
    "Citation",
    "Criterion",
    "CriterionAssessment",
    "Determination",
    "DocumentSet",
    "Freshness",
    "MissingInformation",
    "PolicyMatch",
    "ReviewerAction",
]
