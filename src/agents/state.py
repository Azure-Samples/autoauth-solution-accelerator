"""Typed case state shared by the AutoAuth agents.

Every agent reads from and writes to a :class:`CaseState`. Values the reviewer
must verify carry :class:`Citation` objects so the UI can jump to the evidence
and the eval adapters can turn the state back into legacy ``Evaluation`` rows.

Kept Python 3.10 compatible because ``environment.yaml`` still pins 3.10.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

DecisionLabel = Literal["Approved", "Rejected", "Needs More Information"]
AssessmentLabel = Literal["Fully Met", "Partially Met", "Not Met"]
FreshnessKind = Literal[
    "policy", "clinical_evidence", "provider_affiliation", "member_eligibility"
]
FreshnessStatus = Literal["fresh", "aging", "stale", "unknown"]

# How long each kind of data can be trusted before a reviewer should re-check it.
# Providers change roles and affiliations, members change plans, labs age out.
DEFAULT_MAX_AGE_DAYS: Dict[str, int] = {
    "policy": 365,
    "clinical_evidence": 90,
    "provider_affiliation": 180,
    "member_eligibility": 30,
}
AGING_FRACTION = 0.75
_FRACTION = re.compile(r"\.(\d+)")

FRESHNESS_ACTIONS: Dict[str, str] = {
    "policy": "Confirm this is the current policy version.",
    "clinical_evidence": "Request recent labs or imaging.",
    "provider_affiliation": "Re-verify the provider's NPI, role and affiliation.",
    "member_eligibility": "Re-run the member eligibility check.",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class Freshness(BaseModel):
    """How recently a piece of case data was verified, and whether to re-check it.

    ``as_of`` is the last time the source was known to be correct (blob
    last-modified, NPI registry lookup, eligibility check). ``None`` means nobody
    has verified it, which is surfaced as ``unknown`` rather than assumed fresh.
    """

    kind: FreshnessKind
    subject: str = Field(description="What the signal is about, e.g. a blob URL.")
    as_of: Optional[datetime] = None
    max_age_days: Optional[int] = None
    source: str = "unverified"
    note: Optional[str] = None

    def limit_days(self) -> int:
        return self.max_age_days or DEFAULT_MAX_AGE_DAYS[self.kind]

    def age_days(self, now: Optional[datetime] = None) -> Optional[int]:
        if self.as_of is None:
            return None
        delta = _as_utc(now or _utcnow()) - _as_utc(self.as_of)
        return max(0, delta.days)

    def status(self, now: Optional[datetime] = None) -> FreshnessStatus:
        age = self.age_days(now)
        if age is None:
            return "unknown"
        limit = self.limit_days()
        if age > limit:
            return "stale"
        if age >= limit * AGING_FRACTION:
            return "aging"
        return "fresh"

    def action(self) -> str:
        return FRESHNESS_ACTIONS[self.kind]

    def report(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "subject": self.subject,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "age_days": self.age_days(now),
            "max_age_days": self.limit_days(),
            "status": self.status(now),
            "source": self.source,
            "note": self.note,
            "action": self.action(),
        }

    @classmethod
    def unknown(
        cls, kind: FreshnessKind, subject: str, note: Optional[str] = None
    ) -> "Freshness":
        return cls(kind=kind, subject=subject, note=note)

    @classmethod
    def from_value(
        cls, kind: FreshnessKind, subject: str, value: Any, source: str
    ) -> "Freshness":
        """Build from a datetime or ISO-8601 string; unparseable values are unknown."""
        as_of: Optional[datetime] = None
        if isinstance(value, datetime):
            as_of = value
        elif isinstance(value, str) and value.strip():
            text = _FRACTION.sub(
                lambda m: "." + m.group(1)[:6].ljust(6, "0"),
                value.strip().replace("Z", "+00:00"),
            )
            try:
                as_of = datetime.fromisoformat(text)
            except ValueError:
                as_of = None
        if as_of is None:
            return cls.unknown(kind, subject, note=f"No usable date from {source}.")
        return cls(kind=kind, subject=subject, as_of=as_of, source=source)


class Citation(BaseModel):
    """Pointer to the evidence behind a value."""

    source: str = Field(description="Blob URL, document path or uploaded file name.")
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    quote: Optional[str] = None
    bbox: Optional[List[float]] = None


class PolicyMatch(BaseModel):
    """A policy document the policy agent judged relevant to the case."""

    blob_url: str
    chunk_id: Optional[str] = None
    reasoning: Optional[str] = None
    text: Optional[str] = None
    score: Optional[float] = None
    citations: List[Citation] = Field(default_factory=list)
    freshness: Optional[Freshness] = None

    @classmethod
    def from_text(
        cls, policy_text: str, blob_url: str = "inline://policy"
    ) -> "PolicyMatch":
        """Wrap raw policy text (legacy callers pass text, not matches)."""
        return cls(
            blob_url=blob_url, text=policy_text, citations=[Citation(source=blob_url)]
        )


class Criterion(BaseModel):
    """One coverage requirement extracted from a policy."""

    id: str
    text: str
    citations: List[Citation] = Field(default_factory=list)


class CriterionAssessment(BaseModel):
    """Whether the case evidence satisfies one criterion."""

    criterion_id: str
    status: AssessmentLabel
    evidence: str = ""
    policy_reference: str = ""
    notes: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)


class MissingInformation(BaseModel):
    information_needed: str
    reason: str = ""


class Determination(BaseModel):
    """Final recommendation. A human reviewer always signs it off."""

    decision: DecisionLabel
    rationale: str
    missing_information: List[MissingInformation] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    model: Optional[str] = None
    # Data-freshness flags for the reviewer. Never part of the legacy output.
    warnings: List[str] = Field(default_factory=list)


class ReviewerAction(BaseModel):
    """A reviewer accepting, editing or rejecting a field or decision."""

    field: str
    action: Literal["accept", "edit", "reject"]
    original: Any = None
    corrected: Any = None
    reviewer: Optional[str] = None
    note: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utcnow)


class DocumentSet(BaseModel):
    """Uploaded clinical documents for a case."""

    files: List[str] = Field(default_factory=list)
    pages: Dict[str, int] = Field(default_factory=dict)


class CaseState(BaseModel):
    """Single source of truth for one prior-authorization case."""

    case_id: str
    trace_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created_at: datetime = Field(default_factory=_utcnow)

    documents: DocumentSet = Field(default_factory=DocumentSet)
    patient_information: Dict[str, Any] = Field(default_factory=dict)
    physician_information: Dict[str, Any] = Field(default_factory=dict)
    clinical_information: Dict[str, Any] = Field(default_factory=dict)
    # Keyed by dotted path, e.g. "clinical_information.diagnosis".
    field_citations: Dict[str, List[Citation]] = Field(default_factory=dict)

    expanded_query: Optional[str] = None
    policy_search_reasoning: List[str] = Field(default_factory=list)
    policies: List[PolicyMatch] = Field(default_factory=list)
    criteria: List[Criterion] = Field(default_factory=list)
    assessments: List[CriterionAssessment] = Field(default_factory=list)
    determination: Optional[Determination] = None
    reviewer_actions: List[ReviewerAction] = Field(default_factory=list)
    # Case-level freshness; per-policy freshness lives on PolicyMatch.freshness.
    freshness: List[Freshness] = Field(default_factory=list)

    def all_freshness(self) -> List[Freshness]:
        return list(self.freshness) + [p.freshness for p in self.policies if p.freshness]

    def ensure_freshness_defaults(self) -> None:
        """Flag extracted data nobody has verified as ``unknown``, never as fresh."""
        have = {f.kind for f in self.freshness}
        if self.physician_information and "provider_affiliation" not in have:
            self.freshness.append(
                Freshness.unknown(
                    "provider_affiliation",
                    "physician_information",
                    note="Extracted from the request form (name, specialty, contact); "
                    "no NPI lookup or verification date.",
                )
            )
        if self.patient_information and "member_eligibility" not in have:
            self.freshness.append(
                Freshness.unknown(
                    "member_eligibility",
                    "patient_information",
                    note="No eligibility check recorded for this member.",
                )
            )
        if self.clinical_information and "clinical_evidence" not in have:
            self.freshness.append(
                Freshness.unknown(
                    "clinical_evidence",
                    "clinical_information",
                    note="Lab and imaging dates are not extracted from the documents.",
                )
            )

    def freshness_report(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        return [f.report(now) for f in self.all_freshness()]

    def stale_signals(
        self, now: Optional[datetime] = None, include_unknown: bool = False
    ) -> List[Freshness]:
        flagged = {"stale", "aging"} | ({"unknown"} if include_unknown else set())
        return [f for f in self.all_freshness() if f.status(now) in flagged]

    def all_citations(self) -> List[Citation]:
        """Every citation in the state, de-duplicated, in a stable order."""
        seen = set()
        out: List[Citation] = []
        groups: List[List[Citation]] = list(self.field_citations.values())
        groups += [p.citations for p in self.policies]
        groups += [c.citations for c in self.criteria]
        groups += [a.citations for a in self.assessments]
        if self.determination:
            groups.append(self.determination.citations)
        for items in groups:
            for c in items:
                key = (c.source, c.chunk_id, c.page, c.quote)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
        return out

    def to_legacy_determination(self) -> Dict[str, Any]:
        """Render the determination in the ``summarize_autodetermination`` schema.

        The determination evaluator runs jq queries such as ``.Determination``
        and ``.DetailedAnalysis.PolicyCriteriaAssessment`` against this shape.
        """
        if self.determination is None:
            raise ValueError("CaseState has no determination yet.")
        names = {c.id: c.text for c in self.criteria}
        return {
            "Determination": self.determination.decision,
            "Rationale": self.determination.rationale,
            "DetailedAnalysis": {
                "PolicyCriteriaAssessment": [
                    {
                        "CriterionName": names.get(a.criterion_id, a.criterion_id),
                        "Assessment": a.status,
                        "Evidence": a.evidence,
                        "PolicyReference": a.policy_reference,
                        "Notes": a.notes,
                    }
                    for a in self.assessments
                ],
                "MissingInformation": [
                    {"InformationNeeded": m.information_needed, "Reason": m.reason}
                    for m in self.determination.missing_information
                ],
            },
        }

    def to_legacy_determination_text(self) -> str:
        return json.dumps(self.to_legacy_determination(), ensure_ascii=False)


_SLUG = re.compile(r"[^a-z0-9]+")


def slugify(text: str, max_len: int = 40) -> str:
    """Stable, readable id for criteria extracted from free text."""
    slug = _SLUG.sub("-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-") or "criterion"


def as_dict(value: Any) -> Dict[str, Any]:
    """Accept pydantic models, dicts or JSON strings from legacy callers."""
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
        return loaded if isinstance(loaded, dict) else {"text": value}
    return {"value": value}
