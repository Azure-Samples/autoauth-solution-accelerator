"""Runner factory: one switch between the legacy pipeline and the new agents.

``AUTOAUTH_RUNNER`` selects the implementation:

* ``legacy`` (default) - the original ``ClinicalDataExtractor`` / ``AgenticRAG`` /
  ``AutoPADeterminator`` classes, unchanged. Eval scores stay as they are.
* ``agents`` - the agents in :mod:`src.agents`, wrapped so they return exactly what
  the legacy runners return. The stage evaluators and the YAML eval cases do not
  change, so they score both implementations the same way.
* ``agents-af`` - same agents, with every model call routed through Microsoft
  Agent Framework (requires ``requirements-agents.txt``).

The clinical extractor has no agent replacement yet, so every mode uses the legacy
extractor for that stage.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, List, Optional, Protocol, Tuple

from src.agents.state import CaseState, PolicyMatch, as_dict

logger = logging.getLogger(__name__)

RUNNER_ENV = "AUTOAUTH_RUNNER"
MODES = ("legacy", "agents", "agents-af")
STAGES = {
    "extract": "extract",
    "extractor": "extract",
    "clinical": "extract",
    "policy": "policy",
    "rag": "policy",
    "agenticrag": "policy",
    "determine": "determine",
    "determination": "determine",
}


class ExtractorRunner(Protocol):
    async def run(self, *args: Any, **kwargs: Any) -> Dict[str, Any]: ...


class PolicyRunner(Protocol):
    async def run(self, clinical_info: Any, max_retries: int = 3) -> Dict[str, Any]: ...


class DeterminationRunner(Protocol):
    async def run(
        self,
        patient_info: Any,
        physician_info: Any,
        clinical_info: Any,
        policy_text: str,
        summarize_policy_callback: Callable[[str], Awaitable[str]],
        use_o1: bool = False,
        caseId: Optional[str] = None,
    ) -> Tuple[str, List[Any]]: ...


def runner_mode(mode: Optional[str] = None) -> str:
    value = (mode or os.getenv(RUNNER_ENV) or "legacy").strip().lower()
    if value not in MODES:
        raise ValueError(f"{RUNNER_ENV}={value!r} is not one of {MODES}")
    return value


def resolve_stage(stage: str) -> str:
    try:
        return STAGES[stage.strip().lower()]
    except KeyError:
        raise ValueError(f"Unknown stage {stage!r}; expected one of {sorted(set(STAGES))}") from None


def _llm(mode: str, azure_openai_client: Any = None, llm: Any = None) -> Any:
    if llm is None:
        from src.agents.llm import AOAIJsonLLM

        if azure_openai_client is None:
            from src.aoai.aoai_helper import AzureOpenAIManager

            azure_openai_client = AzureOpenAIManager(api_key=os.getenv("AZURE_OPENAI_KEY"))
        llm = AOAIJsonLLM(azure_openai_client)
    if mode == "agents-af":
        from src.agents.af_binding import AFJsonLLM, JsonLLMChatClient

        llm = AFJsonLLM(JsonLLMChatClient(llm))
    return llm


class PolicyAgentAdapter:
    """``AgenticRAG.run`` signature and return shape over :class:`PolicyAgent`."""

    def __init__(
        self,
        mode: str = "agents",
        azure_openai_client: Any = None,
        prompt_manager: Any = None,
        search_client: Any = None,
        caseId: Optional[str] = None,
        llm: Any = None,
        search: Any = None,
        **_unused: Any,
    ) -> None:
        from src.agents.policy_agent import PolicyAgent, make_azure_search_fn

        if search is None:
            if search_client is None:
                from azure.core.credentials import AzureKeyCredential
                from azure.search.documents import SearchClient

                search_client = SearchClient(
                    endpoint=os.getenv("AZURE_AI_SEARCH_SERVICE_ENDPOINT"),
                    index_name=os.getenv("AZURE_SEARCH_INDEX_NAME"),
                    credential=AzureKeyCredential(os.getenv("AZURE_AI_SEARCH_ADMIN_KEY", "")),
                )
            search = make_azure_search_fn(search_client)
        self.caseId = caseId
        self.agent = PolicyAgent(llm=_llm(mode, azure_openai_client, llm), search=search, prompts=prompt_manager)
        self.last_state: Optional[CaseState] = None

    async def run(self, clinical_info: Any, max_retries: int = 3) -> Dict[str, Any]:
        self.agent.max_attempts = max_retries
        state = CaseState(case_id=self.caseId or "adhoc", clinical_information=as_dict(clinical_info))
        state = await self.agent.run(state)
        self.last_state = state
        if not state.policies:
            return {"query": None, "policies": [], "evaluation": None}
        return {
            "query": state.expanded_query,
            "policies": [p.blob_url for p in state.policies],
            "evaluation": {
                "policies": [p.blob_url for p in state.policies],
                "reasoning": state.policy_search_reasoning,
                "retry": False,
            },
        }


class DeterminationAgentAdapter:
    """``AutoPADeterminator.run`` signature and return shape over the criteria and
    determination agents. Returns ``(json_text, [])``; the JSON uses the same
    schema as ``summarize_autodetermination`` so the evaluator's jq queries work."""

    def __init__(
        self,
        mode: str = "agents",
        azure_openai_client: Any = None,
        caseId: Optional[str] = None,
        llm: Any = None,
        **_unused: Any,
    ) -> None:
        self.mode = mode
        self.caseId = caseId
        self.llm = _llm(mode, azure_openai_client, llm)
        self.last_state: Optional[CaseState] = None

    async def run(
        self,
        patient_info: Any,
        physician_info: Any,
        clinical_info: Any,
        policy_text: str,
        summarize_policy_callback: Optional[Callable[[str], Awaitable[str]]] = None,
        use_o1: bool = False,
        caseId: Optional[str] = None,
    ) -> Tuple[str, List[Any]]:
        from src.agents.criteria_agent import CriteriaAgent
        from src.agents.determination_agent import DeterminationAgent

        if use_o1:
            logger.info("use_o1 is ignored by the agent runner; model choice lives in the LLM binding.")
        state = CaseState(
            case_id=caseId or self.caseId or "adhoc",
            patient_information=as_dict(patient_info),
            physician_information=as_dict(physician_info),
            clinical_information=as_dict(clinical_info),
            policies=[PolicyMatch.from_text(policy_text)] if policy_text else [],
        )
        state = await CriteriaAgent(self.llm, summarize_policy=summarize_policy_callback).run(state)
        state = await DeterminationAgent(self.llm).run(state)
        self.last_state = state
        return state.to_legacy_determination_text(), []


def get_runner(stage: str, mode: Optional[str] = None, **kwargs: Any) -> Any:
    """Build the runner for ``stage``. ``kwargs`` are the legacy constructor arguments;
    agent adapters ignore the ones they do not need."""
    stage = resolve_stage(stage)
    mode = runner_mode(mode)

    if stage == "extract":
        from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor

        return ClinicalDataExtractor(**kwargs)

    if mode == "legacy":
        if stage == "policy":
            from src.pipeline.agenticRag.run import AgenticRAG

            return AgenticRAG(**kwargs)
        from src.pipeline.autoDetermination.run import AutoPADeterminator

        return AutoPADeterminator(**kwargs)

    if stage == "policy":
        return PolicyAgentAdapter(mode=mode, **kwargs)
    return DeterminationAgentAdapter(mode=mode, **kwargs)


def describe() -> str:
    return json.dumps({"mode": runner_mode(), "env": RUNNER_ENV, "modes": list(MODES)})
