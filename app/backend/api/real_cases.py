"""Load the prototype cases in ``utils/data/cases`` into the reviewer UI.

Each ``<NNN>/<a|b>`` folder becomes one case (``CASE-001A`` ...). The pieces come
from the sources the evals already trust:

* documents: text of the case PDFs (policy PDFs capped at a few pages);
* extracted facts: MD-curated values from ``evals/cases/ocr-ner-*.yaml`` where a
  case has one, otherwise the closest ``autodetermination-decision-*.yaml``
  context (chosen by word overlap with the case PDFs);
* decision: the MD ground truth in ``ground_truth.json``. When the PDFs print a
  different scenario label (APPROVAL/DENIAL) the case carries a label-conflict
  warning instead of silently picking one.

Recorded parity runs (``utils/data/cases/parity_runs``) appear in the trace.
"""

from __future__ import annotations

import functools
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import yaml

if TYPE_CHECKING:
    from app.backend.api.demo_data import CaseRecord

from src.agents.state import (
    CaseState,
    Citation,
    Determination,
    DocumentSet,
    Freshness,
    PolicyMatch,
)
from src.evals.adapters.parity import (
    APPROVED,
    CASES_ROOT,
    PrototypeCase,
    discover_cases,
    load_runs,
    runs_dir,
)

logger = logging.getLogger(__name__)

EVAL_ROOT = Path("evals/cases")
POLICY_PAGES = 3
SCANNED = "(scanned page: no text layer; the extractor OCRs this page)"
CTX_PREFIX = "src.pipeline.promptEngineering.models:"
SECTIONS = {
    "PatientInformation": "patient_information",
    "PhysicianInformation": "physician_information",
    "ClinicalInformation": "clinical_information",
}
_DATE_RE = re.compile(
    r"(?:effective|revised|review(?:ed)?|last\s+updated)[^\n]{0,30}?"
    r"(\d{1,2}/\d{1,2}/\d{4}|[A-Z][a-z]+\.? \d{1,2},? \d{4})",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[a-z0-9]{3,}")


@functools.lru_cache(maxsize=128)
def _pdf_pages(path: str, mtime: float, max_pages: Optional[int] = None) -> Tuple[Tuple[str, ...], ...]:
    import pymupdf

    pages = []
    with pymupdf.open(path) as doc:
        for i, page in enumerate(doc):
            if max_pages is not None and i >= max_pages:
                break
            lines = tuple(ln.strip() for ln in page.get_text().splitlines() if ln.strip())
            pages.append(lines or (SCANNED,))
    return tuple(pages)


def pdf_pages(path: Path, max_pages: Optional[int] = None) -> List[List[str]]:
    return [list(p) for p in _pdf_pages(str(path), path.stat().st_mtime, max_pages)]


def _doc_name(path: Path) -> str:
    """``003_a (note) .pdf`` -> ``003_a (note).pdf`` (some names have stray spaces)."""
    return re.sub(r"\s+\.pdf$", ".pdf", path.name.strip())


def _words(text: str) -> set:
    return set(_WORD_RE.findall(text.lower()))


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(v) for v in value)
    return "" if value is None else str(value)


def _set_dotted(target: Dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
        if not isinstance(target, dict):
            return
    target[parts[-1]] = value


@functools.lru_cache(maxsize=1)
def _autodetermination_contexts() -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
    """``{case number: [(eval key, context), ...]}``, one context per pos/neg pair."""
    out: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
    for path in sorted(EVAL_ROOT.glob("autodetermination-decision-*.yaml")):
        number = path.stem.rsplit("-", 1)[-1]
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        seen = set()
        for key, value in data.items():
            if not key.endswith(".v0") or not isinstance(value, dict):
                continue
            ctx = ((value.get("evaluations") or [{}])[0]).get("context") or {}
            facts = {SECTIONS[k[len(CTX_PREFIX):]]: v for k, v in ctx.items() if k[len(CTX_PREFIX):] in SECTIONS}
            fingerprint = _flatten(facts)
            if facts and fingerprint not in seen:
                seen.add(fingerprint)
                out.setdefault(number, []).append((key, facts))
    return out


def _ocr_ner_facts(case: PrototypeCase) -> Tuple[Optional[str], Dict[str, Any]]:
    path = EVAL_ROOT / f"ocr-ner-{case.number}-{case.variant}.yaml"
    if not path.exists():
        return None, {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    facts: Dict[str, Any] = {}
    for key, value in data.items():
        if key.endswith(".v0") and isinstance(value, dict):
            for ev in value.get("evaluations") or []:
                if ev.get("query") and "ground_truth" in ev:
                    _set_dotted(facts, ev["query"], ev["ground_truth"])
    return path.name, facts


def _merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def select_facts(case: PrototypeCase, doc_text: str) -> Tuple[Dict[str, Any], List[str]]:
    """Facts for one case plus the eval files they came from."""
    sources: List[str] = []
    facts: Dict[str, Any] = {}
    candidates = _autodetermination_contexts().get(case.number, [])
    if candidates:
        doc_words = _words(doc_text)

        def overlap(item: Tuple[str, Dict[str, Any]]) -> float:
            words = _words(_flatten(item[1]))
            return len(words & doc_words) / len(words) if words else 0.0

        key, facts = max(candidates, key=overlap)
        sources.append(f"autodetermination-decision-{case.number}.yaml ({key.split('.')[0].rsplit('-', 2)[-2]} context)")
    ocr_file, ocr = _ocr_ner_facts(case)
    if ocr_file:
        facts = _merge(facts, ocr)
        sources.insert(0, ocr_file)
    return facts, sources


def _cite_fields(
    facts: Dict[str, Any], documents: Dict[str, List[List[str]]], prefix: str = ""
) -> Dict[str, List[Citation]]:
    """Cite each scalar fact on the first document line that contains it."""
    cites: Dict[str, List[Citation]] = {}
    for key, value in facts.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            cites.update(_cite_fields(value, documents, path))
            continue
        text = _flatten(value).strip()
        if len(text) < 3:
            continue
        needle = text.lower() if len(text) <= 40 else text[:30].lower()
        hit = _find_line(needle, documents)
        if hit:
            cites[path] = [Citation(source=hit[0], page=hit[1], quote=hit[2])]
    return cites


def _find_line(needle: str, documents: Dict[str, List[List[str]]]) -> Optional[Tuple[str, int, str]]:
    for name, pages in documents.items():
        if name.startswith("policy-"):
            continue
        for p, lines in enumerate(pages, start=1):
            for line in lines:
                if needle in line.lower():
                    return name, p, line
    return None


def _policy_date(pages: List[List[str]]) -> Optional[datetime]:
    match = _DATE_RE.search("\n".join(ln for page in pages for ln in page))
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", "")
    for fmt in ("%m/%d/%Y", "%B %d %Y", "%b %d %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_when(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _request_name(clinical: Dict[str, Any], fallback: str) -> str:
    tr = clinical.get("treatment_request") or {}
    name = str(tr.get("name_of_medication_or_procedure") or fallback).strip()
    return name.split(";")[0].split(",")[0][:48]


def _spans(case: PrototypeCase, runs: Dict[str, Dict[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    spans = [
        {
            "name": "prototype.case",
            "depth": 0,
            "detail": f"utils/data/cases/{case.number}/{case.variant}",
            "seconds": None,
            "signal": "",
            "status": "ok",
        },
        {
            "name": "md_ground_truth",
            "depth": 1,
            "detail": case.ground_truth_note or "ground_truth.json",
            "seconds": None,
            "signal": case.ground_truth or "",
            "status": "ok",
        },
    ]
    for runner, cases in runs.items():
        rec = cases.get(case.case_id)
        if rec is None:
            continue
        spans.append(
            {
                "name": f"parity.{runner}",
                "depth": 1,
                "detail": rec.get("error") or f"recorded {rec.get('recorded_at', '')[:10]}",
                "seconds": rec.get("seconds"),
                "signal": rec.get("decision") or rec.get("status", ""),
                "status": "ok" if rec.get("status") == "ok" else "err",
            }
        )
    spans.append({"name": "human_review", "depth": 1, "detail": "waiting on reviewer", "seconds": None, "signal": "", "status": "wait"})
    return spans


def build_case(case: PrototypeCase, now: datetime, index: int, runs: Dict[str, Dict[str, Dict[str, Any]]]) -> "CaseRecord":
    # demo_data imports this module while seeding its store.
    from app.backend.api.demo_data import CaseRecord, freshness_warnings

    documents: Dict[str, List[List[str]]] = {}
    for path in case.all_files:
        documents[_doc_name(path)] = pdf_pages(path)
    files = list(documents)
    doc_text = "\n".join(ln for name in files for page in documents[name] for ln in page)

    facts, fact_sources = select_facts(case, doc_text)
    patient = dict(facts.get("patient_information") or {})
    physician = dict(facts.get("physician_information") or {})
    clinical = dict(facts.get("clinical_information") or {})
    field_citations = _cite_fields(
        {"patient_information": patient, "physician_information": physician, "clinical_information": clinical},
        documents,
    )

    policies: List[PolicyMatch] = []
    policy_name = None
    if case.policy is not None:
        policy_name = f"policy-{case.number}.pdf"
        pages = pdf_pages(case.policy, POLICY_PAGES)
        documents[policy_name] = pages
        title = next((ln for ln in pages[0] if len(ln) > 12), policy_name) if pages else policy_name
        effective = _policy_date(pages)
        policies.append(
            PolicyMatch(
                blob_url=policy_name,
                chunk_id="p1",
                reasoning=f"Prototype policy for case {case.number}: {title}",
                score=None,
                citations=[Citation(source=policy_name, page=1, quote=title)],
                freshness=Freshness(
                    kind="policy",
                    subject=policy_name,
                    as_of=effective,
                    source="date printed in the policy" if effective else "unverified",
                ),
            )
        )

    evaluated = _parse_when(case.evaluated_at)
    freshness = [
        Freshness(kind="clinical_evidence", subject=name, as_of=evaluated, source="MD evaluation date (ground_truth.json)")
        for name in files
    ]
    if physician.get("physician_name"):
        freshness.append(Freshness(kind="provider_affiliation", subject=str(physician["physician_name"])))
    if patient.get("patient_id"):
        freshness.append(Freshness(kind="member_eligibility", subject=str(patient["patient_id"])))

    case_id = f"CASE-{case.number}{case.variant.upper()}"
    state = CaseState(
        case_id=case_id,
        created_at=now,
        documents=DocumentSet(files=files, pages={n: len(documents[n]) for n in files}),
        patient_information=patient,
        physician_information=physician,
        clinical_information=clinical,
        field_citations=field_citations,
        policies=policies,
        freshness=freshness,
    )

    decision = case.ground_truth or "Needs More Information"
    rationale = f"MD ground truth: {decision.lower()}. {case.ground_truth_note}".strip()
    if case.label_conflict:
        rationale += (
            f" The case PDFs are labelled {case.pdf_label.upper()}, which disagrees with ground_truth.json;"
            " confirm the label before using this case to score parity."
        )
    state.determination = Determination(
        decision="Approved" if decision == APPROVED else "Rejected" if decision == "Denied" else decision,
        rationale=rationale,
        citations=[c for cites in list(field_citations.values())[:2] for c in cites],
        model="MD review (ground truth)",
    )
    state.ensure_freshness_defaults()
    warnings = freshness_warnings(state, now)
    if case.label_conflict:
        warnings.insert(0, f"label conflict: PDFs say {case.pdf_label}, ground_truth.json says {case.ground_truth}")
    state.determination.warnings = warnings

    return CaseRecord(
        state=state,
        patient_name=str(patient.get("patient_name") or case_id),
        request=_request_name(clinical, f"Case {case.number}"),
        urgency="standard",
        received_at=now - timedelta(hours=6 + index * 3),
        provider_org=str(physician.get("specialty") or "Prototype set"),
        line_of_business="Prototype set",
        confidence=None,
        runner="ground_truth",
        documents=documents,
        spans=_spans(case, runs),
        template="prototype",
        prototype={
            "case_key": case.case_id,
            "folder": f"utils/data/cases/{case.number}/{case.variant}",
            "ground_truth": case.ground_truth,
            "pdf_label": case.pdf_label,
            "label_conflict": case.label_conflict,
            "fact_sources": fact_sources,
            "policy": policy_name,
            "notes": case.notes,
        },
    )


def load(now: Optional[datetime] = None, root: Path = CASES_ROOT) -> List["CaseRecord"]:
    """All prototype cases; returns ``[]`` (and logs) when the data or PyMuPDF is missing."""
    now = now or datetime.now(timezone.utc)
    if not root.is_dir():
        return []
    try:
        cases = discover_cases(root)
        runs = load_runs(runs_dir(root))
        return [build_case(c, now, i, runs) for i, c in enumerate(cases)]
    except Exception as e:  # the demo cases still load
        logger.warning("Prototype cases skipped: %s", e)
        return []
