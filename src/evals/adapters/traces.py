"""Turn a finished :class:`CaseState` (a "trace") into eval records.

The YAML cases in ``evals/cases`` stay the source of truth. This adapter lets the
same queries score a run that went through the new agents, and lets reviewer
corrections from the UI become new YAML cases.

Supported query forms, matching the existing stage evaluators:

* Dotted paths such as ``patient_information.patient_name`` (clinical extractor).
* jq expressions starting with ``.`` (for example ``.Determination``), run against
  :meth:`CaseState.to_legacy_determination` (auto-determination).
* Scenario lookups ``policy`` and ``reasoning`` (agentic RAG). Free-text queries
  such as ``"Associated Policies for Positive Scenario"`` need ``scenario=``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Mapping, Optional

from src.agents.state import CaseState

_MISSING = object()


def _dotted(data: Any, path: str) -> Any:
    current = data
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            return _MISSING
    return current


def _jq(expression: str, data: Dict[str, Any]) -> str:
    """Same post-processing as ``AutoDeterminationEvaluator.process_generated_output``."""
    try:
        import jq
    except ImportError:
        value = _dotted(data, expression.lstrip("."))
        if value is _MISSING or "|" in expression:
            raise RuntimeError(
                f"jq is required to evaluate {expression!r}; pip install jq"
            ) from None
        return str(value)
    subset = jq.compile(expression).input(data).all()
    return str(subset[0]) if subset else ""


def policy_response(state: CaseState) -> str:
    """Same shape as ``AgenticRagEvaluator.process_generated_output`` (policy)."""
    return "\n".join("/".join(p.blob_url.split("/")[-2:]) for p in state.policies)


def reasoning_response(state: CaseState) -> str:
    return "\n".join(state.policy_search_reasoning)


class TraceToEvaluation:
    """Builds ``src.evals.case.Evaluation`` records from a :class:`CaseState`."""

    @staticmethod
    def resolve(state: CaseState, query: str, scenario: Optional[str] = None) -> Any:
        if scenario == "policy":
            return policy_response(state)
        if scenario == "reasoning":
            return reasoning_response(state)
        if query.startswith("."):
            return _jq(query, state.to_legacy_determination())
        value = _dotted(state.model_dump(mode="json"), query)
        if value is _MISSING:
            raise KeyError(f"{query!r} is not a path in CaseState")
        return value

    @staticmethod
    def context(state: CaseState) -> str:
        """Citations ride along as eval context so groundedness metrics can use them."""
        return json.dumps(
            {
                "case_id": state.case_id,
                "trace_id": state.trace_id,
                "citations": [c.model_dump(mode="json") for c in state.all_citations()],
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_case_state(
        cls,
        state: CaseState,
        evaluations: Iterable[Mapping[str, Any]],
        scenario: Optional[str] = None,
    ) -> List[Any]:
        """``evaluations`` uses the YAML shape: ``[{query, ground_truth}, ...]``."""
        from src.evals.case import Evaluation

        context = cls.context(state)
        records = []
        for item in evaluations:
            query = str(item["query"])
            try:
                response = cls.resolve(state, query, scenario)
            except (KeyError, ValueError, RuntimeError) as exc:
                response = f"<unresolved: {exc}>"
            records.append(
                Evaluation(
                    query=query,
                    response=response,
                    ground_truth=item.get("ground_truth"),
                    context=context,
                )
            )
        return records

    @classmethod
    def to_case(
        cls,
        state: CaseState,
        case_name: str,
        metrics: List[str],
        evaluations: Iterable[Mapping[str, Any]],
        scenario: Optional[str] = None,
    ) -> Any:
        from src.evals.case import Case

        return Case(
            case_name=case_name,
            metrics=metrics,
            evaluations=cls.from_case_state(state, evaluations, scenario),
        )

    @staticmethod
    def from_reviewer_actions(
        state: CaseState,
        case_name: Optional[str] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Reviewer edits and rejections become a new YAML eval case.

        The corrected value is the ground truth. Accepted fields are skipped
        because they add no new signal. Pass the result to ``yaml.safe_dump``.
        """
        name = case_name or f"reviewer-{state.case_id}-{state.trace_id[:8]}.v0"
        evaluations = []
        for action in state.reviewer_actions:
            if action.action == "accept":
                continue
            field = action.field
            query = ".Determination" if field in ("determination", "decision") else field
            item: Dict[str, Any] = {"query": query, "ground_truth": action.corrected}
            if action.note:
                item["note"] = action.note
            evaluations.append(item)
        return {
            name: {
                "metrics": metrics or ["FuzzyEvaluator"],
                "evaluations": evaluations,
            }
        }
