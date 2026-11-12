"""Reviewer UI API.

Serves the five screens from ``docs/architecture/wireframes/agentic-2026.html``:
queue, case workspace, trace, provider submission and quality. Cases come from
the in-memory demo store (:mod:`app.backend.api.demo_data`). This module never
imports Azure SDKs, so it runs without credentials.

Freshness is advisory. Re-verifying a source updates its ``as_of`` date and
warnings but never changes the recommendation. A "deny" from the reviewer
always routes to medical-director review; there is no automated denial.
"""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.agents.state import CaseState, ReviewerAction
from src.evals.adapters.traces import TraceToEvaluation

from . import real_cases
from .demo_data import (
    FRESHNESS_RANK,
    SLA_HOURS,
    STAGE_AGENTS,
    STAGES,
    CaseRecord,
    freshness_warnings,
    store,
    submitted_case,
    utcnow,
)

router = APIRouter(prefix="/api", tags=["reviewer-ui"])

EVAL_CASES_DIR = Path(__file__).resolve().parents[3] / "evals" / "cases"
DECISION_LABELS = {
    "Approved": "Approve",
    "Rejected": "Deny",
    "Needs More Information": "Need more info",
}
WORKFLOW_STEPS = ["Intake", "Extract", "Policy", "Criteria", "Recommend", "Human review", "Decision letter"]


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #


class ActionIn(BaseModel):
    field: str
    action: Literal["accept", "edit", "reject"]
    original: Any = None
    corrected: Any = None
    reviewer: Optional[str] = "reviewer"
    note: Optional[str] = None


class DecisionIn(BaseModel):
    decision: Literal["approve", "pend", "deny"]
    reviewer: Optional[str] = "reviewer"
    note: Optional[str] = None


class SubmitIn(BaseModel):
    patient_name: str = Field(min_length=1)
    member_id: str = ""
    drug: str = Field(min_length=1)
    urgency: Literal["expedited", "standard"] = "standard"
    prescriber: str = ""
    specialty: str = ""
    provider_org: str = "My practice"
    files: List[str] = Field(default_factory=lambda: ["request.pdf"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1)


class AssignIn(BaseModel):
    owner: Optional[str] = None


# --------------------------------------------------------------------------- #
# Serializers
# --------------------------------------------------------------------------- #


def _get(case_id: str) -> CaseRecord:
    record = store.get(case_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    return record


def _freshness_summary(record: CaseRecord, now: datetime) -> Dict[str, Any]:
    if record.status == "running":
        return {"overall": "pending", "counts": {}, "label": "pending"}
    counts: Dict[str, int] = {}
    for item in record.state.freshness_report(now):
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    flagged = [s for s in ("stale", "unknown", "aging") if counts.get(s)]
    overall = min(counts, key=lambda s: FRESHNESS_RANK.get(s, 3)) if counts else "unknown"
    label = " · ".join(f"{counts[s]} {s}" for s in flagged) if flagged else "all fresh"
    return {"overall": overall, "counts": counts, "label": label}


def _recommendation(record: CaseRecord) -> Optional[Dict[str, Any]]:
    det = record.state.determination
    if record.status == "running" or det is None:
        return None
    met = sum(1 for a in record.state.assessments if a.status == "Fully Met")
    return {
        "decision": det.decision,
        "label": DECISION_LABELS.get(det.decision, det.decision),
        "confidence": record.confidence,
        "criteria_met": met,
        "criteria_total": len(record.state.assessments),
        "model": det.model,
        "warnings": det.warnings,
    }


def _summary(record: CaseRecord, now: datetime) -> Dict[str, Any]:
    done = record.stages_done(now)
    running = record.status == "running"
    return {
        "case_id": record.state.case_id,
        "trace_id": record.state.trace_id,
        "patient_name": record.patient_name,
        "member_id": record.state.patient_information.get("patient_id"),
        "request": record.request,
        "urgency": record.urgency,
        "line_of_business": record.line_of_business,
        "provider_org": record.provider_org,
        "status": record.status,
        "owner": record.owner,
        "received_at": record.received_at.isoformat(),
        "sla_hours": record.sla_hours(),
        "sla_left_hours": record.sla_left_hours(now),
        "progress": {
            "done": done,
            "total": len(STAGES),
            "current": STAGE_AGENTS[STAGES[done]] if running and done < len(STAGES) else None,
        },
        "recommendation": _recommendation(record),
        "freshness": _freshness_summary(record, now),
        "human_decision": record.human_decision,
        "runner": record.runner,
        "prototype": record.prototype,
        "upload": record.upload,
    }


def _workflow(record: CaseRecord, now: datetime) -> List[Dict[str, str]]:
    if record.status == "running":
        current = record.stages_done(now)
    elif record.human_decision is None:
        current = 5
    else:
        current = 6
    return [
        {"name": name, "state": "done" if i < current else "current" if i == current else "todo"}
        for i, name in enumerate(WORKFLOW_STEPS)
    ]


def _detail(record: CaseRecord, now: datetime) -> Dict[str, Any]:
    state = record.state
    criteria = {c.id: c for c in state.criteria}
    assessments = []
    for a in state.assessments:
        crit = criteria.get(a.criterion_id)
        assessments.append(
            {
                **a.model_dump(mode="json"),
                "criterion_text": crit.text if crit else a.criterion_id,
                "policy_citations": [c.model_dump(mode="json") for c in crit.citations] if crit else [],
            }
        )
    return {
        **_summary(record, now),
        "workflow": _workflow(record, now),
        "documents": record.documents,
        "patient_information": state.patient_information,
        "physician_information": state.physician_information,
        "clinical_information": state.clinical_information,
        "field_citations": {k: [c.model_dump(mode="json") for c in v] for k, v in state.field_citations.items()},
        "policies": [
            {**p.model_dump(mode="json", exclude={"freshness"}), "freshness": p.freshness.report(now) if p.freshness else None}
            for p in state.policies
        ],
        "assessments": assessments,
        "determination": state.determination.model_dump(mode="json") if state.determination else None,
        "freshness_report": [] if record.status == "running" else state.freshness_report(now),
        "reviewer_actions": [a.model_dump(mode="json") for a in state.reviewer_actions],
        "chat": record.chat,
    }


def _trace(record: CaseRecord, now: datetime) -> Dict[str, Any]:
    spans = record.spans
    if record.status == "running":
        done = record.stages_done(now)
        spans = [{"name": "workflow.pa_case", "depth": 0, "detail": "", "seconds": None, "signal": "", "status": "run"}]
        for i, stage in enumerate(STAGES):
            spans.append(
                {
                    "name": STAGE_AGENTS[stage],
                    "depth": 1,
                    "detail": stage,
                    "seconds": None,
                    "signal": "",
                    "status": "ok" if i < done else "run" if i == done else "todo",
                }
            )
    total = spans[0]["seconds"] if spans and spans[0].get("seconds") else None
    return {
        "case_id": record.state.case_id,
        "trace_id": record.state.trace_id,
        "runner": record.runner,
        "total_seconds": total,
        "estimated_cost_usd": 0.38 if record.state.case_id == "PA-1042" else None,
        "spans": spans,
    }


def _refresh_warnings(state: CaseState, now: datetime) -> None:
    if state.determination is not None:
        # Keep non-freshness advisories (e.g. ground-truth label conflicts) across re-verification.
        kept = [w for w in state.determination.warnings if w.startswith(("label conflict", "partial upload"))]
        state.determination.warnings = kept + freshness_warnings(state, now)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #


@router.get("/cases")
def list_cases(
    status: Optional[str] = None,
    urgency: Optional[str] = None,
    freshness: Optional[str] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    now = utcnow()
    rows = [_summary(r, now) for r in store.all(now)]
    if status:
        rows = [r for r in rows if r["status"] == status]
    if urgency:
        rows = [r for r in rows if r["urgency"] == urgency]
    if freshness == "flagged":
        rows = [r for r in rows if r["freshness"]["overall"] in ("stale", "unknown", "aging")]
    if q:
        needle = q.lower()
        rows = [
            r for r in rows
            if needle in " ".join([r["case_id"], r["patient_name"], r["request"]]).lower()
        ]
    rows.sort(key=lambda r: r["sla_left_hours"])
    return {"cases": rows, "generated_at": now.isoformat()}


@router.post("/cases", status_code=201)
def submit_case(body: SubmitIn) -> Dict[str, Any]:
    now = utcnow()
    record = submitted_case(
        store.new_case_id(),
        now,
        body.patient_name,
        body.member_id,
        body.drug,
        body.urgency,
        body.prescriber,
        body.specialty,
        body.provider_org,
        body.files or ["request.pdf"],
    )
    store.add(record)
    return _summary(record, now)


MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@router.get("/samples")
def list_samples() -> Dict[str, Any]:
    """Demo claim packets from utils/data/cases that the upload flow recognizes."""
    seeded = {r.prototype["case_key"]: r for r in store.all() if r.template == "prototype"}
    out = []
    for key, case in sorted(real_cases.scenarios().items()):
        rec = seeded.get(key)
        out.append(
            {
                "key": key,
                "label": f"{case.number}{case.variant.upper()}",
                "ground_truth": case.ground_truth,
                "patient_name": rec.patient_name if rec else None,
                "request": rec.request if rec else None,
                "files": [
                    {"kind": kind, "name": real_cases._doc_name(p), "size": p.stat().st_size}
                    for kind, paths in sorted(case.files.items())
                    for p in paths
                ],
            }
        )
    return {"samples": out}


@router.get("/samples/{key}/files/{name}")
def sample_file(key: str, name: str) -> FileResponse:
    path = real_cases.sample_file(key, name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No sample file {name!r} in {key}.")
    return FileResponse(path, media_type="application/pdf", filename=name)


@router.post("/cases/upload", status_code=201)
async def upload_case(
    files: List[UploadFile] = File(...),
    urgency: Literal["standard", "expedited"] = Form("standard"),
    provider_org: str = Form("My practice"),
) -> Dict[str, Any]:
    """Accept a claim packet. The run is simulated: the PDFs are matched to a demo
    scenario and the case finishes with that scenario's MD ground truth."""
    now = utcnow()
    matches, documents = [], {}
    for f in files:
        name = Path(f.filename or "upload.pdf").name
        data = await f.read()
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"{name} is over 25 MB.")
        try:
            pages = real_cases.extract_pages(data)
        except Exception:
            raise HTTPException(status_code=400, detail=f"{name} is not a readable PDF.")
        documents[name] = pages
        matches.append(real_cases.match_upload(name, data, pages))
    key = real_cases.pick_scenario(matches)
    names = list(documents)
    record = submitted_case(
        store.new_case_id(), now, "Pending extraction", "", "Uploaded claim", urgency,
        "", "", provider_org, names,
    )
    record.template = "upload"
    record.line_of_business = "Uploaded claim"
    record.documents = documents
    record.state.documents.pages = {n: len(p) for n, p in documents.items()}
    record.upload = {"case_key": key, "files": matches}
    store.add(record)
    return _summary(record, now)


@router.get("/cases/{case_id}")
def get_case(case_id: str) -> Dict[str, Any]:
    now = utcnow()
    record = _get(case_id)
    with store.lock():
        return _detail(record, now)


@router.post("/cases/{case_id}/assign")
def assign(case_id: str, body: AssignIn) -> Dict[str, Any]:
    now = utcnow()
    record = _get(case_id)
    with store.lock():
        record.owner = body.owner
        return _summary(record, now)


@router.post("/cases/{case_id}/actions")
def reviewer_action(case_id: str, body: ActionIn) -> Dict[str, Any]:
    record = _get(case_id)
    with store.lock():
        action = ReviewerAction(**body.model_dump())
        record.state.reviewer_actions.append(action)
        if body.action == "edit" and body.field.count(".") == 1:
            section, key = body.field.split(".")
            target = getattr(record.state, section, None)
            if isinstance(target, dict):
                target[key] = body.corrected
        return {
            "action": action.model_dump(mode="json"),
            "reviewer_actions": len(record.state.reviewer_actions),
        }


@router.post("/cases/{case_id}/reverify/{kind}")
def reverify(case_id: str, kind: str) -> Dict[str, Any]:
    """Simulated re-verification (NPPES, X12 270/271, document refresh)."""
    now = utcnow()
    record = _get(case_id)
    sources = {
        "provider_affiliation": "NPPES re-verified (demo)",
        "member_eligibility": "X12 270/271 (demo)",
        "clinical_evidence": "Updated note requested (demo)",
        "policy": "Policy library re-indexed (demo)",
    }
    if kind not in sources:
        raise HTTPException(status_code=400, detail=f"Unknown freshness kind: {kind}")
    with store.lock():
        matches = [f for f in record.state.all_freshness() if f.kind == kind]
        if not matches:
            raise HTTPException(status_code=404, detail=f"No {kind} signal on {case_id}.")
        for item in matches:
            item.as_of = now
            item.source = sources[kind]
        _refresh_warnings(record.state, now)
        return {
            "freshness_report": record.state.freshness_report(now),
            "warnings": record.state.determination.warnings if record.state.determination else [],
            "freshness": _freshness_summary(record, now),
        }


@router.post("/cases/{case_id}/decision")
def decide(case_id: str, body: DecisionIn) -> Dict[str, Any]:
    now = utcnow()
    record = _get(case_id)
    with store.lock():
        if record.status == "running":
            raise HTTPException(status_code=409, detail="Case is still running.")
        status = {"approve": "approved", "pend": "pended", "deny": "md_review"}[body.decision]
        record.status = status
        record.human_decision = {
            "decision": body.decision,
            "status": status,
            "reviewer": body.reviewer,
            "note": body.note,
            "at": now.isoformat(),
        }
        det = record.state.determination
        if det is not None:
            agreed = {"approve": "Approved", "pend": "Needs More Information"}.get(body.decision)
            if agreed != det.decision:
                record.state.reviewer_actions.append(
                    ReviewerAction(
                        field="determination",
                        action="edit" if agreed else "reject",
                        original=det.decision,
                        corrected=agreed or "Rejected",
                        reviewer=body.reviewer,
                        note=body.note or ("Routed to medical director review." if body.decision == "deny" else None),
                    )
                )
        for span in record.spans:
            if span["name"] == "human_review":
                span.update(status="ok", detail=f"{body.decision} by {body.reviewer}")
        return _summary(record, now)


@router.get("/cases/{case_id}/trace")
def get_trace(case_id: str) -> Dict[str, Any]:
    now = utcnow()
    record = _get(case_id)
    with store.lock():
        return _trace(record, now)


@router.post("/cases/{case_id}/eval-case")
def save_eval_case(case_id: str) -> Dict[str, Any]:
    """Turn reviewer edits into a YAML eval case for the existing harness."""
    record = _get(case_id)
    with store.lock():
        case = TraceToEvaluation.from_reviewer_actions(record.state)
    name = next(iter(case))
    return {
        "name": name,
        "evaluations": len(case[name]["evaluations"]),
        "case": case,
        "yaml": yaml.safe_dump(case, sort_keys=False, allow_unicode=True),
    }


@router.get("/cases/{case_id}/events")
async def case_events(case_id: str, poll_seconds: float = 0.5, max_seconds: float = 120.0) -> StreamingResponse:
    """Server-sent events with stage progress until the run finishes."""
    _get(case_id)

    async def stream():
        last = None
        waited = 0.0
        while True:
            now = utcnow()
            record = store.get(case_id, now)
            if record is None:
                return
            with store.lock():
                summary = _summary(record, now)
            key = (summary["status"], summary["progress"]["done"])
            if key != last:
                last = key
                yield f"event: progress\ndata: {json.dumps(summary)}\n\n"
            if summary["status"] != "running" or waited >= max_seconds:
                yield f"event: done\ndata: {json.dumps({'case_id': case_id, 'status': summary['status']})}\n\n"
                return
            await asyncio.sleep(poll_seconds)
            waited += poll_seconds

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _chat_answer(record: CaseRecord, message: str, now: datetime) -> Dict[str, Any]:
    """Grounded, deterministic answers. Only cites what the case already holds."""
    state = record.state
    text = message.lower()
    by_id = {a.criterion_id: a for a in state.assessments}
    names = {c.id: c.text for c in state.criteria}

    def criterion_reply(a) -> Dict[str, Any]:
        lines = [f"{names.get(a.criterion_id, a.criterion_id)}: {a.status}.", f"Evidence: {a.evidence}"]
        if a.notes:
            lines.append(a.notes)
        return {"text": " ".join(lines), "citations": [c.model_dump(mode="json") for c in a.citations]}

    keywords = {
        "conventional-therapy": ("c3", "steroid", "conventional", "therapy", "immunomodulator"),
        "tb-screening": ("c5", "tb", "tuberculosis"),
        "gi-specialist": ("c4", "specialist"),
        "age": ("c2", "age"),
        "diagnosis": ("c1", "diagnosis"),
    }
    tokens = set(re.findall(r"[a-z0-9]+", text))
    for cid, words in keywords.items():
        if cid in by_id and any(w in tokens or (len(w) > 3 and w in text) for w in words):
            return criterion_reply(by_id[cid])

    if any(w in text for w in ("network", "gomez", "provider", "npi", "affiliation", "stale", "fresh")):
        items = [f for f in state.all_freshness() if f.kind in ("provider_affiliation", "member_eligibility")]
        parts = []
        for f in items:
            age = f.age_days(now)
            when = f"{age}d ago" if age is not None else "never"
            status = f.status(now)
            advice = "" if status == "fresh" else f" {f.action()}"
            parts.append(f"{f.subject}: {f.kind.replace('_', ' ')} last verified {when} ({status}).{advice}")
        return {"text": " ".join(parts) or "No freshness signals recorded.", "citations": []}

    if any(w in text for w in ("missing", "request info", "draft", "pend")):
        missing = state.determination.missing_information if state.determination else []
        if not missing:
            return {"text": "Nothing is listed as missing for this case.", "citations": []}
        lines = [f"Please provide {m.information_needed}. {m.reason}" for m in missing]
        return {"text": "Draft info request: " + " ".join(lines), "citations": []}

    return {
        "text": (
            "I can only answer from this case's documents, policy and checks. "
            "Ask about a criterion (C1–C5), missing information, or provider and eligibility freshness."
        ),
        "citations": [],
    }


@router.post("/cases/{case_id}/chat")
def chat(case_id: str, body: ChatIn) -> Dict[str, Any]:
    now = utcnow()
    record = _get(case_id)
    with store.lock():
        if record.status == "running":
            raise HTTPException(status_code=409, detail="Case is still running.")
        reply = _chat_answer(record, body.message, now)
        record.chat.append({"role": "user", "text": body.message, "at": now.isoformat()})
        record.chat.append({"role": "assistant", **reply, "at": now.isoformat()})
        return {"reply": reply, "chat": record.chat}


def _suite_summary(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    suite_name = path.stem
    suite = data.get(suite_name)
    if not isinstance(suite, dict):
        return None
    pipeline = suite.get("pipeline") or {}
    case_names = suite.get("cases") or []
    evaluations = sum(len((data.get(c) or {}).get("evaluations") or []) for c in case_names)
    return {
        "suite": suite_name,
        "family": suite_name.rsplit("-", 1)[0].rstrip("-0123456789") or suite_name,
        "pipeline": pipeline.get("class"),
        "evaluators": [e.get("name") for e in suite.get("evaluators") or []],
        "cases": len(case_names),
        "evaluations": evaluations,
    }


@router.get("/quality")
def quality() -> Dict[str, Any]:
    now = utcnow()
    suites = [s for s in (_suite_summary(p) for p in sorted(EVAL_CASES_DIR.glob("*.yaml"))) if s]
    families: Dict[str, Dict[str, Any]] = {}
    for s in suites:
        fam = families.setdefault(s["family"], {"family": s["family"], "suites": 0, "evaluations": 0, "evaluators": set()})
        fam["suites"] += 1
        fam["evaluations"] += s["evaluations"]
        fam["evaluators"].update(s["evaluators"])
    records = store.all(now)
    overrides = sum(
        1 for r in records for a in r.state.reviewer_actions if a.action in ("edit", "reject")
    )
    decided = [r for r in records if r.human_decision]
    stale_cases = sum(1 for r in records if _freshness_summary(r, now)["overall"] in ("stale", "aging"))
    return {
        "suites": suites,
        "families": [
            {**f, "evaluators": sorted(f["evaluators"])} for f in families.values()
        ],
        # Placeholder numbers until live eval runs are wired in. Label them as such in the UI.
        "illustrative_scores": {
            "note": "Illustrative only. Run `python -m src.evals.pipeline` for real scores.",
            "rows": [
                {"family": "ocr-ner", "baseline": 0.88, "candidate": 0.88},
                {"family": "agentic-rag", "baseline": 0.75, "candidate": 0.81},
                {"family": "autodetermination", "baseline": 0.93, "candidate": 0.93},
            ],
            "online": {"groundedness": 0.91, "task_adherence": 0.87},
        },
        "live": {
            "cases": len(records),
            "reviewer_overrides": overrides,
            "decided": len(decided),
            "stale_input_cases": stale_cases,
            "pend_rate": round(sum(1 for r in decided if r.status == "pended") / len(decided), 2) if decided else None,
        },
        "freshness_limits_days": {
            "policy": 365,
            "clinical_evidence": 90,
            "provider_affiliation": 180,
            "member_eligibility": 30,
        },
        "sla_hours": SLA_HOURS,
    }


@router.get("/parity")
def parity() -> Dict[str, Any]:
    """MD ground truth vs. recorded legacy/agents runs on the prototype cases."""
    from src.evals.adapters.parity import parity_report

    report = parity_report()
    ids = {r.prototype["case_key"]: r.state.case_id for r in store.all() if r.template == "prototype"}
    for row in report["cases"]:
        row["ui_case_id"] = ids.get(row["case_id"])
    return report


@router.post("/demo/reset")
def reset_demo() -> Dict[str, Any]:
    store.reset()
    return {"cases": len(store.all())}
