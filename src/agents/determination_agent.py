"""Determination agent: decision + rationale from the assessed criteria.

The LLM writes the rationale and lists missing information. The decision rule from
``prior_auth_system_prompt.jinja`` is then enforced in code so a model cannot
approve a case with an unmet criterion:

* any criterion "Not Met" or "Partially Met"  -> Rejected
* no criteria / no policy                     -> Needs More Information
* otherwise the model's decision stands (the rule only blocks unsafe approvals)
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.agents.llm import JsonLLM
from src.agents.state import CaseState, Determination, MissingInformation

logger = logging.getLogger(__name__)

SYSTEM = """You are a prior-authorization reviewer writing the final recommendation.
Decide "Approved", "Rejected" or "Needs More Information".
Rules: if any criterion is "Not Met" or "Partially Met", the request is "Rejected".
Use "Needs More Information" only when patient or physician details are unclear or
ambiguous. A human reviewer signs off every decision.
Return JSON: {"decision": "...", "rationale": "...",
"missing_information": [{"information_needed": "...", "reason": "..."}]}"""

_DECISIONS = {
    "approved": "Approved",
    "approve": "Approved",
    "rejected": "Rejected",
    "denied": "Rejected",
    "deny": "Rejected",
    "needs more information": "Needs More Information",
    "more information needed": "Needs More Information",
}


def normalize_decision(value: object) -> str:
    return _DECISIONS.get(str(value or "").strip().lower(), "Needs More Information")


def enforce_rule(state: CaseState, proposed: str) -> str:
    if not state.policies or not state.assessments:
        return "Needs More Information"
    if any(a.status != "Fully Met" for a in state.assessments):
        return "Rejected"
    return proposed


class DeterminationAgent:
    name = "determination_agent"

    def __init__(
        self,
        llm: JsonLLM,
        model_name: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> None:
        self.llm = llm
        self.model_name = model_name
        self.params = {"max_tokens": max_tokens, "temperature": temperature, "top_p": top_p}

    async def run(self, state: CaseState) -> CaseState:
        names = {c.id: c.text for c in state.criteria}
        summary = [
            {
                "criterion": names.get(a.criterion_id, a.criterion_id),
                "status": a.status,
                "evidence": a.evidence,
            }
            for a in state.assessments
        ]
        out = await self.llm(
            system=SYSTEM,
            user=(
                f"Requested treatment: {json.dumps(state.clinical_information.get('treatment_request'), default=str)}\n"
                f"Policies: {[p.blob_url for p in state.policies]}\n"
                f"Criteria assessments:\n{json.dumps(summary, indent=2)}\n"
                f"Patient: {json.dumps(state.patient_information, default=str)}\n"
                f"Physician: {json.dumps(state.physician_information, default=str)}"
            ),
            **self.params,
        )
        proposed = normalize_decision(out.get("decision"))
        decision = enforce_rule(state, proposed)
        rationale = str(out.get("rationale") or "")
        if decision != proposed:
            logger.info("%s: rule changed %s -> %s", self.name, proposed, decision)
            rationale = (rationale + f" [Decision rule applied: {proposed} -> {decision}.]").strip()

        missing = [
            MissingInformation(
                information_needed=str(m.get("information_needed") or ""),
                reason=str(m.get("reason") or ""),
            )
            for m in out.get("missing_information") or []
            if isinstance(m, dict) and m.get("information_needed")
        ]
        if decision == "Needs More Information" and not state.policies:
            missing.append(
                MissingInformation(
                    information_needed="Applicable coverage policy",
                    reason="No policy matching the requested treatment was found.",
                )
            )

        cites = []
        for a in state.assessments:
            if a.status != "Fully Met" or decision == "Approved":
                cites.extend(a.citations)
        state.ensure_freshness_defaults()
        state.determination = Determination(
            decision=decision,
            rationale=rationale,
            missing_information=missing,
            citations=cites,
            model=self.model_name,
            # Advisory only: freshness never changes the decision or rationale.
            warnings=[
                f"{f.kind} ({f.status()}): {f.action()}"
                for f in state.stale_signals(include_unknown=True)
            ],
        )
        return state
