"""Parity harness for the prototype cases in ``utils/data/cases``.

Compares each runner (``legacy``, ``agents``, ``agents-af``) against the MD
ground truth in ``ground_truth.json``. Recorded runs live in
``utils/data/cases/parity_runs/<runner>.json`` so the reviewer UI can show
parity without Azure access; the CLI records them when Azure is configured::

    python -m src.evals.adapters.parity                      # report only
    python -m src.evals.adapters.parity --run legacy agents  # run, record, report

The PDFs also carry their own scenario label (for example
``ADALIMUMAB PA EXAMPLE A (APPROVAL)``). When it disagrees with the MD ground
truth the case is flagged as a label conflict; parity still scores against the
ground truth file, which stays the source of truth.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from src.evals.adapters.runners import MODES

CASES_ROOT = Path("utils/data/cases")
DOC_KINDS = ("pa_form", "doctor_notes", "imaging", "labs")
APPROVED, DENIED, NMI = "Approved", "Denied", "Needs More Information"

_LABEL_RE = re.compile(r"EXAMPLE\s+[A-Z]\s*\((APPROVAL|DENIAL)\)", re.IGNORECASE)
_DECISION_RE = re.compile(
    r"\b(needs?\s+more\s+information|approved?|approval|denied|deny|denial|rejected?)\b",
    re.IGNORECASE,
)


def normalize_decision(value: Any) -> Optional[str]:
    """Map ground truth, eval labels and runner output to Approved/Denied/NMI."""
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("Determination", "determination", "decision", "Decision"):
            if key in value:
                return normalize_decision(value[key])
        return None
    if hasattr(value, "decision"):
        return normalize_decision(getattr(value, "decision"))
    text = str(value).strip()
    if text.startswith("{"):
        try:
            return normalize_decision(json.loads(text))
        except ValueError:
            pass
    match = _DECISION_RE.search(text)
    if not match:
        return None
    word = match.group(1).lower()
    if word.startswith("need"):
        return NMI
    if word.startswith("appro"):
        return APPROVED
    return DENIED


@dataclass
class PrototypeCase:
    """One prototype case folder (``utils/data/cases/<NNN>/<a|b>``)."""

    case_id: str
    number: str
    variant: str
    files: Dict[str, List[Path]]
    policy: Optional[Path]
    ground_truth: Optional[str]
    ground_truth_note: str = ""
    evaluated_at: Optional[str] = None
    pdf_label: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def all_files(self) -> List[Path]:
        return [p for kind in DOC_KINDS for p in self.files.get(kind, [])]

    @property
    def label_conflict(self) -> bool:
        return bool(self.pdf_label and self.ground_truth and self.pdf_label != self.ground_truth)


def _pdf_first_page(path: Path) -> str:
    try:
        import pymupdf
    except ImportError:  # pragma: no cover - optional dependency
        return ""
    try:
        with pymupdf.open(path) as doc:
            return doc[0].get_text() if doc.page_count else ""
    except Exception:
        return ""


def pdf_label(paths: Iterable[Path]) -> Optional[str]:
    """Scenario label printed in the case PDFs (APPROVAL/DENIAL), if any."""
    for path in paths:
        match = _LABEL_RE.search(_pdf_first_page(path))
        if match:
            return APPROVED if match.group(1).upper() == "APPROVAL" else DENIED
    return None


def load_ground_truth(root: Path = CASES_ROOT) -> Dict[str, Dict[str, Any]]:
    path = root / "ground_truth.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def discover_cases(root: Path = CASES_ROOT, read_labels: bool = True) -> List[PrototypeCase]:
    """Find every ``<NNN>/<variant>`` folder; file names are globbed, never assumed."""
    truth = load_ground_truth(root)
    cases: List[PrototypeCase] = []
    for number_dir in sorted(p for p in root.iterdir() if p.is_dir() and p.name.isdigit()):
        for variant_dir in sorted(p for p in number_dir.iterdir() if p.is_dir()):
            case_id = f"{number_dir.name}_{variant_dir.name}"
            files = {
                kind: sorted((variant_dir / kind).glob("*.pdf"))
                for kind in DOC_KINDS
                if (variant_dir / kind).is_dir()
            }
            files = {k: v for k, v in files.items() if v}
            policy = root / "policies" / f"{number_dir.name}.pdf"
            gt = truth.get(case_id, {})
            case = PrototypeCase(
                case_id=case_id,
                number=number_dir.name,
                variant=variant_dir.name,
                files=files,
                policy=policy if policy.exists() else None,
                ground_truth=normalize_decision(gt.get("decision")),
                ground_truth_note=gt.get("notes", ""),
                evaluated_at=gt.get("evaluation_time"),
            )
            if read_labels:
                case.pdf_label = pdf_label(case.all_files)
            listed = {Path(p.replace("\\", "/")).name for k in DOC_KINDS for p in gt.get(k, [])}
            actual = {p.name for p in case.all_files}
            if listed and listed != actual:
                case.notes.append("ground_truth.json file list differs from the folder contents")
            cases.append(case)
    return cases


# --------------------------------------------------------------------------- #
# Recorded runs
# --------------------------------------------------------------------------- #


def runs_dir(root: Path = CASES_ROOT) -> Path:
    return Path(os.getenv("AUTOAUTH_PARITY_RUNS", str(root / "parity_runs")))


def load_runs(directory: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """``{runner: {case_id: record}}`` from ``<runner>.json`` files."""
    runs: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not directory.is_dir():
        return runs
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        runs[path.stem] = data.get("cases", {}) if isinstance(data, dict) else {}
    return runs


def record_run(directory: Path, runner: str, case_id: str, record: Dict[str, Any]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{runner}.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data.setdefault("runner", runner)
    data.setdefault("cases", {})[case_id] = record
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def parity_report(
    root: Path = CASES_ROOT,
    directory: Optional[Path] = None,
    runners: Iterable[str] = MODES,
    cases: Optional[List[PrototypeCase]] = None,
) -> Dict[str, Any]:
    """Per-case and per-runner agreement with the MD ground truth."""
    cases = cases if cases is not None else discover_cases(root)
    runs = load_runs(directory or runs_dir(root))
    runners = list(dict.fromkeys([*runners, *runs]))
    rows = []
    for case in cases:
        results = {}
        for runner in runners:
            rec = runs.get(runner, {}).get(case.case_id)
            if rec is None:
                results[runner] = {"status": "not_run", "decision": None, "match": None}
                continue
            decision = normalize_decision(rec.get("decision"))
            status = rec.get("status", "ok" if decision else "error")
            results[runner] = {
                "status": status,
                "decision": decision,
                "match": (decision == case.ground_truth) if decision and case.ground_truth else None,
                "seconds": rec.get("seconds"),
                "recorded_at": rec.get("recorded_at"),
                "error": rec.get("error"),
            }
        rows.append(
            {
                "case_id": case.case_id,
                "number": case.number,
                "variant": case.variant,
                "files": {k: [p.name for p in v] for k, v in case.files.items()},
                "policy": case.policy.name if case.policy else None,
                "ground_truth": case.ground_truth,
                "ground_truth_note": case.ground_truth_note,
                "pdf_label": case.pdf_label,
                "label_conflict": case.label_conflict,
                "notes": case.notes,
                "results": results,
            }
        )
    summary = {}
    for runner in runners:
        scored = [r["results"][runner] for r in rows if r["results"][runner]["match"] is not None]
        matched = sum(1 for r in scored if r["match"])
        summary[runner] = {
            "run": sum(1 for r in rows if r["results"][runner]["status"] != "not_run"),
            "scored": len(scored),
            "matched": matched,
            "rate": round(matched / len(scored), 3) if scored else None,
        }
    return {
        "cases": rows,
        "runners": runners,
        "summary": summary,
        "label_conflicts": [r["case_id"] for r in rows if r["label_conflict"]],
        "source": "utils/data/cases/ground_truth.json",
        "command": "python -m src.evals.adapters.parity --run legacy agents",
    }


# --------------------------------------------------------------------------- #
# Live runs (requires the Azure resources from azd up and a populated .env)
# --------------------------------------------------------------------------- #


async def run_case(case: PrototypeCase, runner: str) -> Dict[str, Any]:
    """Run one case through ``PAProcessingPipeline`` with ``AUTOAUTH_RUNNER=runner``."""
    os.environ["AUTOAUTH_RUNNER"] = runner
    started = time.time()
    record: Dict[str, Any] = {"recorded_at": datetime.now(timezone.utc).isoformat()}
    try:
        from src.pipeline.paprocessing.run import PAProcessingPipeline

        pipeline = PAProcessingPipeline(send_cloud_logs=False)
        case_key = f"parity-{runner}-{case.case_id}"
        await pipeline.run([str(p) for p in case.all_files], caseId=case_key)
        output = pipeline.results.get(case_key, {})
        raw = output.get("pa_determination_results")
        record.update(
            decision=normalize_decision(raw),
            status="ok" if raw is not None else "error",
            raw=raw if isinstance(raw, (str, dict)) else str(raw),
        )
        if raw is None:
            record["error"] = "Pipeline produced no determination; check the pipeline logs."
    except Exception as e:  # recorded so the UI shows why a runner failed
        record.update(decision=None, status="error", error=f"{type(e).__name__}: {e}")
    record["seconds"] = round(time.time() - started, 1)
    return record


def _print_report(report: Dict[str, Any]) -> None:
    runners = report["runners"]
    print(f"{'case':8} {'MD truth':10} {'PDF label':10} " + " ".join(f"{r:12}" for r in runners))
    for row in report["cases"]:
        cells = []
        for r in runners:
            res = row["results"][r]
            mark = "" if res["match"] is None else (" ok" if res["match"] else " x")
            cells.append(f"{(res['decision'] or res['status'])[:9] + mark:12}")
        flag = " !" if row["label_conflict"] else ""
        print(f"{row['case_id']:8} {row['ground_truth'] or '-':10} {(row['pdf_label'] or '-') + flag:10} " + " ".join(cells))
    for r, s in report["summary"].items():
        rate = "n/a" if s["rate"] is None else f"{s['rate']:.0%}"
        print(f"{r}: {s['matched']}/{s['scored']} match ({rate}), {s['run']} run")
    if report["label_conflicts"]:
        print("Label conflicts (PDF label != MD ground truth): " + ", ".join(report["label_conflicts"]))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run", nargs="*", choices=MODES, default=[], help="runners to execute before reporting")
    parser.add_argument("--cases", nargs="*", default=None, help="case ids such as 001_a (default: all)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    args = parser.parse_args(argv)

    cases = discover_cases()
    if args.cases:
        cases = [c for c in cases if c.case_id in set(args.cases)]
    if args.run:
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass
        if not os.getenv("AZURE_OPENAI_ENDPOINT"):
            print("AZURE_OPENAI_ENDPOINT is not set. Deploy with azd up and populate .env first.", file=sys.stderr)
            return 2
        directory = runs_dir()
        for runner in args.run:
            for case in cases:
                print(f"running {runner} on {case.case_id}...", file=sys.stderr)
                record_run(directory, runner, case.case_id, asyncio.run(run_case(case, runner)))
    report = parity_report(cases=cases)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        _print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
