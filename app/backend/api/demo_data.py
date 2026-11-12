"""In-memory case store and fictional seed data for the reviewer UI.

Every case is a real :class:`~src.agents.state.CaseState`, so the API serves the
same shape the agents produce and the eval adapters consume. Patients, members
and providers are fictional. Field names follow the OCR eval cases
(``evals/cases/ocr-ner-*.yaml``) so reviewer edits become valid eval queries.

Submitted cases run through a simulated pipeline whose stages advance with
wall-clock time (``AUTOAUTH_DEMO_STAGE_SECONDS``). No Azure calls are made.
"""

from __future__ import annotations

import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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
)

STAGES = ["intake", "extract", "policy", "criteria", "recommend"]
STAGE_AGENTS = {
    "intake": "intake_agent",
    "extract": "clinical_extractor",
    "policy": "policy_agent",
    "criteria": "criteria_agent",
    "recommend": "determination_agent",
}
# CMS-0057-F decision clocks.
SLA_HOURS = {"expedited": 72, "standard": 168}
DEMO_MODEL = "<reasoning-model>"
FRESHNESS_RANK = {"stale": 0, "unknown": 1, "aging": 2, "fresh": 3}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stage_seconds_default() -> float:
    return float(os.getenv("AUTOAUTH_DEMO_STAGE_SECONDS", "2"))


def freshness_warnings(state: CaseState, now: Optional[datetime] = None) -> List[str]:
    """Same advisory format the determination agent writes, one line per kind/status."""
    return list(
        dict.fromkeys(
            f"{f.kind} ({f.status(now)}): {f.action()}"
            for f in state.stale_signals(now, include_unknown=True)
        )
    )


@dataclass
class CaseRecord:
    """A case plus the queue metadata the UI needs and the agents do not."""

    state: CaseState
    patient_name: str
    request: str
    urgency: str
    received_at: datetime
    provider_org: str
    line_of_business: str = "Commercial"
    owner: Optional[str] = None
    confidence: Optional[float] = None
    status: str = "ready"  # running | ready | pended | approved | md_review
    runner: str = "agents"
    documents: Dict[str, List[List[str]]] = field(default_factory=dict)
    spans: List[Dict[str, Any]] = field(default_factory=list)
    chat: List[Dict[str, Any]] = field(default_factory=list)
    human_decision: Optional[Dict[str, Any]] = None
    run_started_at: Optional[datetime] = None
    stage_seconds: float = 2.0
    stage_offset: int = 0
    template: str = "generic"
    # Set for cases loaded from utils/data/cases (see real_cases.py).
    prototype: Optional[Dict[str, Any]] = None
    # Set for claim uploads: per-file scenario matches (see real_cases.match_upload).
    upload: Optional[Dict[str, Any]] = None
    def sla_hours(self) -> int:
        return SLA_HOURS.get(self.urgency, SLA_HOURS["standard"])

    def sla_left_hours(self, now: datetime) -> float:
        due = self.received_at + timedelta(hours=self.sla_hours())
        return round((due - now).total_seconds() / 3600, 1)

    def stages_done(self, now: datetime) -> int:
        if self.status != "running" or self.run_started_at is None:
            return len(STAGES)
        if self.stage_seconds <= 0:
            return len(STAGES)
        elapsed = (now - self.run_started_at).total_seconds()
        return min(len(STAGES), self.stage_offset + int(elapsed // self.stage_seconds))


# --------------------------------------------------------------------------- #
# Documents (page -> lines). Citations quote these lines verbatim.
# --------------------------------------------------------------------------- #

POLICY_HUMIRA = "Humira_Crohns_v3.pdf"
POLICY_GENERIC = "Pharmacy_General_Criteria_v7.pdf"

Q_DX = "Assessment: Crohn's disease, ileocolonic (K50.90)."
Q_TX = "Methylprednisolone 40mg daily x 8 wks, inadequate response; flare on taper."
Q_MD = "Signed: R. Gomez MD, Gastroenterology, Lakeside GI Assoc."
Q_PLAN = "Plan: start adalimumab 160/80/40 induction, then 40mg q2w."
Q_DOB = "DOB: 2004-03-12"
Q_MEMBER = "Member ID: W12345678"
Q_HGB = "Hemoglobin 10.1 g/dL (L)  CRP 38 mg/L (H)"
P_A = "§A Diagnosis of moderately to severely active Crohn's disease."
P_AGE = "§A.2 Patient is 6 years of age or older."
P_B = (
    "§B Inadequate response to at least one conventional therapy: "
    "systemic corticosteroids OR an immunomodulator."
)
P_C = "§C Prescribed by or in consultation with a gastroenterologist."
P_D = "§D Negative TB screening documented before the first dose."

HUMIRA_DOCS: Dict[str, List[List[str]]] = {
    "form.pdf": [
        [
            "PRIOR AUTHORIZATION REQUEST · page 1 of 1",
            "Patient: Sarah Sample",
            Q_DOB,
            Q_MEMBER,
            "Plan: Contoso Health Commercial PPO",
            "",
            "Requested: Adalimumab 40mg/0.4mL pen",
            "Urgency: Expedited",
            "Prescriber: R. Gomez MD · NPI 1234567893",
            "Office: 200 Lakeside Dr, Suite 4, Springfield",
        ]
    ],
    "note.pdf": [
        [
            "CLINICAL NOTE · page 1 of 3 · 2026-09-01",
            "Pt: Sarah Sample  DOB 2004-03-12",
            "",
            Q_DX,
            "",
            Q_TX,
            "Azathioprine not trialed; patient declined.",
            "",
            Q_MD,
            "",
            Q_PLAN,
        ],
        [
            "CLINICAL NOTE · page 2 of 3",
            "HPI: 6-8 loose stools/day with blood, abdominal pain, 4kg weight loss.",
            "Colonoscopy 2026-08-20: ileocolonic ulceration, SES-CD 14.",
        ],
        [
            "CLINICAL NOTE · page 3 of 3",
            "Follow up in 4 weeks after induction.",
        ],
    ],
    "labs.pdf": [
        [
            "LAB REPORT · collected 2026-08-18",
            Q_HGB,
            "Albumin 3.1 g/dL (L)",
            "Fecal calprotectin 820 ug/g (H)",
        ]
    ],
    POLICY_HUMIRA: [
        ["HUMIRA (adalimumab) · Crohn's disease · v3 · page 1", "Coverage overview."],
        [
            "HUMIRA (adalimumab) · Crohn's disease · v3 · page 2",
            P_A,
            P_AGE,
            P_B,
            P_C,
            P_D,
        ],
    ],
}


def _cite(source: str, quote: str, page: int = 1) -> Citation:
    return Citation(source=source, page=page, quote=quote)


# --------------------------------------------------------------------------- #
# Case builders
# --------------------------------------------------------------------------- #


def _humira_state(case_id: str, now: datetime) -> CaseState:
    c_dx = _cite("note.pdf", Q_DX)
    c_tx = _cite("note.pdf", Q_TX)
    c_md = _cite("note.pdf", Q_MD)
    c_plan = _cite("note.pdf", Q_PLAN)
    c_dob = _cite("form.pdf", Q_DOB)
    c_member = _cite("form.pdf", Q_MEMBER)
    c_labs = _cite("labs.pdf", Q_HGB)
    policy_cites = {
        key: _cite(POLICY_HUMIRA, quote, page=2)
        for key, quote in {"A": P_A, "AGE": P_AGE, "B": P_B, "C": P_C, "D": P_D}.items()
    }

    state = CaseState(
        case_id=case_id,
        created_at=now - timedelta(hours=58),
        documents=DocumentSet(
            files=["form.pdf", "note.pdf", "labs.pdf"],
            pages={"form.pdf": 1, "note.pdf": 3, "labs.pdf": 1},
        ),
        patient_information={
            "patient_name": "Sarah Sample",
            "patient_date_of_birth": "2004-03-12",
            "patient_id": "W12345678",
        },
        physician_information={
            "physician_name": "R. Gomez MD",
            "specialty": "Gastroenterology",
            "physician_contact": {"office_address": "Lakeside GI Assoc."},
        },
        clinical_information={
            "diagnosis": "Crohn's disease, ileocolonic",
            "icd_10_code": "K50.90",
            "prior_treatments_and_results": (
                "Methylprednisolone 40mg daily x 8 wks; inadequate response, flare on taper"
            ),
            "requested_medication": "Adalimumab",
            "dosage": "160/80/40 induction, then 40mg q2w",
            "relevant_lab_results_or_imaging": "Hemoglobin 10.1 g/dL; CRP 38 mg/L",
        },
        field_citations={
            "patient_information.patient_name": [_cite("form.pdf", "Patient: Sarah Sample")],
            "patient_information.patient_date_of_birth": [c_dob],
            "patient_information.patient_id": [c_member],
            "physician_information.physician_name": [c_md],
            "physician_information.specialty": [c_md],
            "clinical_information.diagnosis": [c_dx],
            "clinical_information.icd_10_code": [c_dx],
            "clinical_information.prior_treatments_and_results": [c_tx],
            "clinical_information.requested_medication": [c_plan],
            "clinical_information.dosage": [c_plan],
            "clinical_information.relevant_lab_results_or_imaging": [c_labs],
        },
        expanded_query="adalimumab Crohn's disease prior authorization criteria",
        policy_search_reasoning=[
            "Searched 'adalimumab Crohn's' and 'TNF inhibitor IBD'.",
            "Humira_Crohns_v3 covers the diagnosis and drug; ranked first.",
        ],
        policies=[
            PolicyMatch(
                blob_url=POLICY_HUMIRA,
                chunk_id="p2",
                reasoning="Drug and diagnosis match; criteria on page 2.",
                score=0.93,
                citations=list(policy_cites.values()),
                freshness=Freshness(
                    kind="policy",
                    subject=POLICY_HUMIRA,
                    as_of=now - timedelta(days=41),
                    source="blob last_modified",
                ),
            )
        ],
        criteria=[
            Criterion(id="diagnosis", text="Diagnosis of Crohn's disease", citations=[policy_cites["A"]]),
            Criterion(id="age", text="Age 6 or older", citations=[policy_cites["AGE"]]),
            Criterion(
                id="conventional-therapy",
                text="Failed at least one conventional therapy",
                citations=[policy_cites["B"]],
            ),
            Criterion(id="gi-specialist", text="Prescriber is a GI specialist", citations=[policy_cites["C"]]),
            Criterion(id="tb-screening", text="TB screening documented", citations=[policy_cites["D"]]),
        ],
        assessments=[
            CriterionAssessment(
                criterion_id="diagnosis",
                status="Fully Met",
                evidence=Q_DX,
                policy_reference="§A",
                citations=[c_dx],
            ),
            CriterionAssessment(
                criterion_id="age",
                status="Fully Met",
                evidence="DOB 2004-03-12 (22 years).",
                policy_reference="§A.2",
                citations=[c_dob],
            ),
            CriterionAssessment(
                criterion_id="conventional-therapy",
                status="Partially Met",
                evidence=Q_TX,
                policy_reference="§B",
                notes=(
                    "Steroid failure is documented. Azathioprine was declined, not failed. "
                    "The policy says OR, so the requirement is satisfied."
                ),
                citations=[c_tx, policy_cites["B"]],
            ),
            CriterionAssessment(
                criterion_id="gi-specialist",
                status="Fully Met",
                evidence=Q_MD,
                policy_reference="§C",
                notes="Affiliation was last verified 212 days ago.",
                citations=[c_md],
            ),
            CriterionAssessment(
                criterion_id="tb-screening",
                status="Not Met",
                evidence="No matching evidence found in 3 documents.",
                policy_reference="§D",
                citations=[policy_cites["D"]],
            ),
        ],
        freshness=[
            Freshness(
                kind="clinical_evidence",
                subject="note.pdf",
                as_of=now - timedelta(days=71),
                source="document date",
                note="Most recent clinical note.",
            ),
            Freshness(
                kind="provider_affiliation",
                subject="R. Gomez MD · NPI 1234567893",
                as_of=now - timedelta(days=212),
                source="NPPES lookup",
                note="Dr. Gomez may have changed practice.",
            ),
            Freshness.unknown(
                "member_eligibility",
                "W12345678",
                note="No eligibility check recorded for this member.",
            ),
        ],
    )
    state.determination = Determination(
        decision="Approved",
        rationale=(
            "Diagnosis of Crohn's disease is documented. "
            "Inadequate response to systemic steroids satisfies the conventional-therapy requirement. "
            "TB screening is not documented; pend for info if the policy requires it before the first dose."
        ),
        missing_information=[
            MissingInformation(
                information_needed="TB screening result",
                reason="Policy §D requires a negative TB screen before the first dose.",
            )
        ],
        citations=[c_dx, c_tx, policy_cites["D"]],
        model=DEMO_MODEL,
    )
    state.determination.warnings = freshness_warnings(state, now)
    return state


def _humira_spans() -> List[Dict[str, Any]]:
    return [
        {"name": "workflow.pa_case", "depth": 0, "detail": "", "seconds": 41.2, "signal": "", "status": "ok"},
        {"name": "intake_agent", "depth": 1, "detail": "ocr.analyze(3 docs)", "seconds": 6.1, "signal": "", "status": "ok"},
        {
            "name": "clinical_extractor",
            "depth": 1,
            "detail": "extract(Patient, Physician, Clinical) · legacy",
            "seconds": 9.8,
            "signal": "conf .92",
            "status": "ok",
        },
        {"name": "policy_agent", "depth": 1, "detail": "search ×2 · judge ×2 (1 retry)", "seconds": 8.4, "signal": "top-3", "status": "ok"},
        {"name": "freshness", "depth": 2, "detail": "policy last_modified 41d → fresh", "seconds": None, "signal": "fresh", "status": "ok"},
        {"name": "criteria_agent", "depth": 1, "detail": "policy → 5 criteria", "seconds": 5.0, "signal": "", "status": "ok"},
        {
            "name": "determination_agent",
            "depth": 1,
            "detail": "reasoning model · advisory freshness warnings",
            "seconds": 11.9,
            "signal": "0.86",
            "status": "ok",
        },
        {"name": "human_review", "depth": 1, "detail": "waiting on reviewer", "seconds": None, "signal": "", "status": "wait"},
    ]


def _generic_state(
    case_id: str,
    now: datetime,
    patient_name: str,
    member_id: str,
    drug: str,
    prescriber: str,
    specialty: str,
    files: List[str],
    decision: str,
    freshness: List[Freshness],
) -> CaseState:
    first = files[0] if files else "request.pdf"
    request_quote = f"Requested: {drug}"
    c_req = _cite(first, request_quote)
    p_cite = _cite(POLICY_GENERIC, f"§1 {drug} requires documented medical necessity.", page=1)
    status = "Fully Met" if decision == "Approved" else "Partially Met"
    state = CaseState(
        case_id=case_id,
        created_at=now,
        documents=DocumentSet(files=files, pages={f: 1 for f in files}),
        patient_information={"patient_name": patient_name, "patient_id": member_id},
        physician_information={"physician_name": prescriber, "specialty": specialty},
        clinical_information={"requested_medication": drug},
        field_citations={
            "patient_information.patient_name": [c_req],
            "clinical_information.requested_medication": [c_req],
        },
        policies=[
            PolicyMatch(
                blob_url=POLICY_GENERIC,
                chunk_id="p1",
                reasoning=f"General pharmacy criteria apply to {drug}.",
                score=0.71,
                citations=[p_cite],
                freshness=Freshness(
                    kind="policy",
                    subject=POLICY_GENERIC,
                    as_of=now - timedelta(days=120),
                    source="blob last_modified",
                ),
            )
        ],
        criteria=[
            Criterion(id="medical-necessity", text="Medical necessity documented", citations=[p_cite])
        ],
        assessments=[
            CriterionAssessment(
                criterion_id="medical-necessity",
                status=status,
                evidence=request_quote,
                policy_reference="§1",
                citations=[c_req],
            )
        ],
        freshness=freshness,
    )
    missing = []
    if decision == "Needs More Information":
        missing = [
            MissingInformation(
                information_needed=f"Clinical notes supporting {drug}",
                reason="Only the request form was found.",
            )
        ]
    state.determination = Determination(
        decision=decision,
        rationale=f"{drug}: medical necessity is {status.lower()} per the general criteria.",
        missing_information=missing,
        citations=[c_req, p_cite],
        model=DEMO_MODEL,
    )
    state.ensure_freshness_defaults()
    state.determination.warnings = freshness_warnings(state, now)
    return state


def _generic_docs(drug: str, patient_name: str, files: List[str]) -> Dict[str, List[List[str]]]:
    docs: Dict[str, List[List[str]]] = {}
    for i, name in enumerate(files or ["request.pdf"]):
        lines = [f"{name.upper()} · page 1 of 1", f"Patient: {patient_name}"]
        if i == 0:
            lines.append(f"Requested: {drug}")
        docs[name] = [lines]
    docs[POLICY_GENERIC] = [
        ["GENERAL PHARMACY CRITERIA · v7 · page 1", f"§1 {drug} requires documented medical necessity."]
    ]
    return docs


def _generic_spans(confidence: float) -> List[Dict[str, Any]]:
    spans = [{"name": "workflow.pa_case", "depth": 0, "detail": "", "seconds": 18.0, "signal": "", "status": "ok"}]
    for stage, seconds in zip(STAGES, [3.0, 4.0, 4.5, 2.5, 4.0]):
        spans.append(
            {"name": STAGE_AGENTS[stage], "depth": 1, "detail": stage, "seconds": seconds, "signal": "", "status": "ok"}
        )
    spans[-1]["signal"] = f"{confidence:.2f}"
    spans.append({"name": "human_review", "depth": 1, "detail": "waiting on reviewer", "seconds": None, "signal": "", "status": "wait"})
    return spans


def finalize_run(record: CaseRecord, now: datetime) -> None:
    """Fill a running case with results once its simulated stages finish."""
    s = record.state
    files = s.documents.files or ["request.pdf"]
    if record.template == "upload":
        from app.backend.api import real_cases

        if (record.upload or {}).get("case_key"):
            built = real_cases.build_for_upload(record, now)
            for name in ("state", "documents", "spans", "patient_name", "request", "prototype",
                         "line_of_business", "runner", "confidence"):
                setattr(record, name, getattr(built, name))
        else:
            real_cases.build_unmatched(record, now)
            record.patient_name = "Unidentified member"
            record.request = "Unclassified request"
            record.spans = _generic_spans(0.0)
            record.spans[-2]["signal"] = "no match"
    elif record.template == "humira":
        fresh = _humira_state(s.case_id, now)
        fresh.trace_id, fresh.created_at = s.trace_id, s.created_at
        fresh.patient_information["patient_name"] = record.patient_name
        record.state = fresh
        record.documents = dict(HUMIRA_DOCS)
        record.spans = _humira_spans()
        record.confidence = 0.86
    else:
        prescriber = s.physician_information.get("physician_name", "Unknown prescriber")
        record.state = _generic_state(
            s.case_id,
            now,
            record.patient_name,
            s.patient_information.get("patient_id", ""),
            record.request,
            prescriber,
            s.physician_information.get("specialty", ""),
            files,
            "Needs More Information",
            [],
        )
        record.state.trace_id = s.trace_id
        record.documents = _generic_docs(record.request, record.patient_name, files)
        record.confidence = 0.52
        record.spans = _generic_spans(record.confidence)
    record.status = "ready"
    record.run_started_at = None


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #


class CaseStore:
    """Thread-safe in-memory store. ``reset()`` restores the seed cases."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._cases: Dict[str, CaseRecord] = {}
        self._next = 1043
        self.reset()

    def reset(self, now: Optional[datetime] = None) -> None:
        with self._lock:
            self._cases = {r.state.case_id: r for r in seed_cases(now or utcnow())}
            self._next = 1043

    def lock(self) -> threading.RLock:
        return self._lock

    def all(self, now: Optional[datetime] = None) -> List[CaseRecord]:
        now = now or utcnow()
        with self._lock:
            for record in self._cases.values():
                self._advance(record, now)
            return list(self._cases.values())

    def get(self, case_id: str, now: Optional[datetime] = None) -> Optional[CaseRecord]:
        with self._lock:
            record = self._cases.get(case_id)
            if record is not None:
                self._advance(record, now or utcnow())
            return record

    def add(self, record: CaseRecord) -> CaseRecord:
        with self._lock:
            self._cases[record.state.case_id] = record
            return record

    def new_case_id(self) -> str:
        with self._lock:
            case_id = f"PA-{self._next}"
            self._next += 1
            return case_id

    @staticmethod
    def _advance(record: CaseRecord, now: datetime) -> None:
        if record.status == "running" and record.stages_done(now) >= len(STAGES):
            finalize_run(record, now)


def submitted_case(
    case_id: str,
    now: datetime,
    patient_name: str,
    member_id: str,
    drug: str,
    urgency: str,
    prescriber: str,
    specialty: str,
    provider_org: str,
    files: List[str],
    stage_seconds: Optional[float] = None,
) -> CaseRecord:
    template = "humira" if any(k in drug.lower() for k in ("adalimumab", "humira")) else "generic"
    state = CaseState(
        case_id=case_id,
        created_at=now,
        documents=DocumentSet(files=files, pages={f: 1 for f in files}),
        patient_information={"patient_name": patient_name, "patient_id": member_id},
        physician_information={"physician_name": prescriber, "specialty": specialty},
    )
    return CaseRecord(
        state=state,
        patient_name=patient_name,
        request=drug,
        urgency=urgency,
        received_at=now,
        provider_org=provider_org,
        status="running",
        runner="demo",
        run_started_at=now,
        stage_seconds=stage_seconds_default() if stage_seconds is None else stage_seconds,
        template=template,
    )


def seed_cases(now: datetime) -> List[CaseRecord]:
    pa1042 = CaseRecord(
        state=_humira_state("PA-1042", now),
        patient_name="Sarah Sample",
        request="Adalimumab",
        urgency="expedited",
        received_at=now - timedelta(hours=58),
        provider_org="Lakeside GI Assoc.",
        confidence=0.86,
        documents=dict(HUMIRA_DOCS),
        spans=_humira_spans(),
    )
    pa1042.state.trace_id = "7f3a9c2e" + uuid.uuid4().hex[8:]

    files_1039 = ["request.pdf", "xray-report.pdf"]
    pa1039 = CaseRecord(
        state=_generic_state(
            "PA-1039",
            now,
            "Juan Example",
            "M98765432",
            "MRI L-spine",
            "T. Ortiz MD",
            "Orthopedics",
            files_1039,
            "Needs More Information",
            [
                Freshness(kind="clinical_evidence", subject="xray-report.pdf", as_of=now - timedelta(days=70), source="document date"),
                Freshness(kind="provider_affiliation", subject="T. Ortiz MD", as_of=now - timedelta(days=30), source="NPPES lookup"),
                Freshness(kind="member_eligibility", subject="M98765432", as_of=now - timedelta(days=3), source="X12 270/271"),
            ],
        ),
        patient_name="Juan Example",
        request="MRI L-spine",
        urgency="standard",
        received_at=now - timedelta(hours=72),
        provider_org="Northside Ortho",
        owner="JL",
        confidence=0.45,
        documents=_generic_docs("MRI L-spine", "Juan Example", files_1039),
        spans=_generic_spans(0.45),
    )

    files_1031 = ["request.pdf", "derm-note.pdf"]
    pa1031 = CaseRecord(
        state=_generic_state(
            "PA-1031",
            now,
            "Lee Fictional",
            "C24681357",
            "Dupilumab",
            "A. Chen MD",
            "Dermatology",
            files_1031,
            "Approved",
            [
                Freshness(kind="clinical_evidence", subject="derm-note.pdf", as_of=now - timedelta(days=12), source="document date"),
                Freshness(kind="provider_affiliation", subject="A. Chen MD", as_of=now - timedelta(days=20), source="NPPES lookup"),
                Freshness(kind="member_eligibility", subject="C24681357", as_of=now - timedelta(days=2), source="X12 270/271"),
            ],
        ),
        patient_name="Lee Fictional",
        request="Dupilumab",
        urgency="standard",
        received_at=now - timedelta(hours=48),
        provider_org="Bayview Dermatology",
        owner="MK",
        confidence=0.94,
        documents=_generic_docs("Dupilumab", "Lee Fictional", files_1031),
        spans=_generic_spans(0.94),
    )
    pa1031.state.policies[0].freshness.as_of = now - timedelta(days=60)

    # Advances slowly so the queue visibly updates during a demo.
    pa1037 = submitted_case(
        "PA-1037",
        now - timedelta(hours=24),
        "Ana Placeholder",
        "S11223344",
        "Semaglutide",
        "standard",
        "P. Singh MD",
        "Endocrinology",
        "Riverside Endocrine",
        ["request.pdf", "a1c-labs.pdf"],
        stage_seconds=90,
    )
    pa1037.run_started_at = now
    pa1037.stage_offset = 3
    pa1037.runner = "agents"

    seeded = [pa1042, pa1039, pa1037, pa1031]
    if os.getenv("AUTOAUTH_PROTOTYPE_CASES", "1") != "0":
        from app.backend.api import real_cases

        seeded += real_cases.load(now)
    return seeded


store = CaseStore()
