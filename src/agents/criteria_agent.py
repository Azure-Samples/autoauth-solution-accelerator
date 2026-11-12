"""Criteria agent: turn policy text into explicit criteria, then assess each one.

The legacy determinator does this implicitly inside one large prompt. Splitting it
gives the reviewer a checklist with evidence and citations per criterion, and lets
the determination agent apply the decision rule deterministically.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

from src.agents.llm import ContextLengthExceeded, JsonLLM
from src.agents.state import (
    CaseState,
    Citation,
    Criterion,
    CriterionAssessment,
    PolicyMatch,
    slugify,
)

logger = logging.getLogger(__name__)

SummarizeFn = Callable[[str], Awaitable[str]]

_STATUSES = {"fully met": "Fully Met", "partially met": "Partially Met", "not met": "Not Met"}

EXTRACT_SYSTEM = """You are a prior-authorization policy analyst.
Extract every coverage criterion a request must satisfy for the requested treatment.
Only use requirements stated in the policy text. Do not invent criteria.
Return JSON: {"criteria": [{"id": "short-kebab-id", "text": "the requirement",
"policy_reference": "section or quote", "source": "policy URL if known"}]}"""

ASSESS_SYSTEM = """You are a prior-authorization clinical reviewer.
For each criterion decide whether the case evidence satisfies it.
Use "Fully Met", "Partially Met" or "Not Met". If the evidence does not demonstrate
a criterion (for example prior or alternative treatments), it is "Not Met".
Quote the evidence you relied on and name the case fields it came from.
Return JSON: {"assessments": [{"criterion_id": "...", "status": "Fully Met",
"evidence": "...", "policy_reference": "...", "notes": "...",
"source_fields": ["clinical_information.prior_treatments_and_results"]}]}"""


def policy_corpus(policies: List[PolicyMatch]) -> str:
    parts = []
    for p in policies:
        if p.text:
            parts.append(f"### Policy: {p.blob_url}\n{p.text}")
    return "\n\n".join(parts)


def _status(value: Any) -> str:
    return _STATUSES.get(str(value or "").strip().lower(), "Not Met")


class CriteriaAgent:
    name = "criteria_agent"

    def __init__(
        self,
        llm: JsonLLM,
        summarize_policy: Optional[SummarizeFn] = None,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> None:
        self.llm = llm
        self.summarize_policy = summarize_policy
        self.params = {"max_tokens": max_tokens, "temperature": temperature, "top_p": top_p}

    async def _call_with_summary(self, system: str, build_user: Callable[[str], str], text: str) -> Dict[str, Any]:
        try:
            return await self.llm(system=system, user=build_user(text), **self.params)
        except ContextLengthExceeded:
            if not self.summarize_policy:
                raise
            logger.info("%s: policy too long, summarizing", self.name)
            return await self.llm(
                system=system, user=build_user(await self.summarize_policy(text)), **self.params
            )

    async def extract(self, state: CaseState) -> List[Criterion]:
        corpus = policy_corpus(state.policies)
        if not corpus:
            return []
        clinical = state.clinical_information.get("treatment_request") or {}
        out = await self._call_with_summary(
            EXTRACT_SYSTEM,
            lambda text: (
                f"Requested treatment: {json.dumps(clinical, default=str)}\n\n"
                f"Diagnosis: {state.clinical_information.get('diagnosis')}\n\n"
                f"Policy text:\n{text}"
            ),
            corpus,
        )
        default_source = state.policies[0].blob_url
        criteria: List[Criterion] = []
        seen = set()
        for raw in out.get("criteria") or []:
            text = str(raw.get("text") or "").strip()
            if not text:
                continue
            cid = slugify(str(raw.get("id") or text))
            while cid in seen:
                cid += "-x"
            seen.add(cid)
            criteria.append(
                Criterion(
                    id=cid,
                    text=text,
                    citations=[
                        Citation(
                            source=str(raw.get("source") or default_source),
                            quote=str(raw.get("policy_reference") or text),
                        )
                    ],
                )
            )
        return criteria

    def _evidence_citations(self, state: CaseState, fields: List[str], evidence: str) -> List[Citation]:
        cites: List[Citation] = []
        for f in fields:
            known = state.field_citations.get(f)
            cites.extend(known or [Citation(source=f"case://{state.case_id}/{f}", quote=evidence or None)])
        return cites

    async def assess(self, state: CaseState) -> List[CriterionAssessment]:
        if not state.criteria:
            return []
        case = {
            "patient_information": state.patient_information,
            "physician_information": state.physician_information,
            "clinical_information": state.clinical_information,
        }
        crit = [{"id": c.id, "text": c.text} for c in state.criteria]
        out = await self.llm(
            system=ASSESS_SYSTEM,
            user=(
                f"Criteria:\n{json.dumps(crit, indent=2)}\n\n"
                f"Case evidence:\n{json.dumps(case, indent=2, default=str)}"
            ),
            **self.params,
        )
        by_id = {str(a.get("criterion_id")): a for a in out.get("assessments") or []}
        results = []
        for c in state.criteria:
            raw = by_id.get(c.id)
            if raw is None:
                results.append(
                    CriterionAssessment(
                        criterion_id=c.id,
                        status="Not Met",
                        notes="No assessment returned; treated as not demonstrated.",
                        policy_reference=c.citations[0].quote if c.citations else "",
                    )
                )
                continue
            evidence = str(raw.get("evidence") or "")
            fields = [str(f) for f in raw.get("source_fields") or []]
            results.append(
                CriterionAssessment(
                    criterion_id=c.id,
                    status=_status(raw.get("status")),
                    evidence=evidence,
                    policy_reference=str(raw.get("policy_reference") or ""),
                    notes=raw.get("notes"),
                    citations=self._evidence_citations(state, fields, evidence) + c.citations,
                )
            )
        return results

    async def run(self, state: CaseState) -> CaseState:
        state.criteria = await self.extract(state)
        state.assessments = await self.assess(state)
        return state
