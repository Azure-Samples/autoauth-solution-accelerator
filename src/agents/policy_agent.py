"""Policy agent: expand -> search -> judge, with citations and feedback on retry.

Behavioural successor to ``src.pipeline.agenticRag.run.AgenticRAG``. It reuses
the same Jinja prompts and search formatting so the existing ``AgenticRagEvaluator``
scores stay comparable, and adds three things the legacy loop lacks:

* the judge's reasoning from a failed attempt is fed into the next expansion,
* every approved policy carries chunk-level :class:`Citation` objects,
* results land in a typed :class:`CaseState` instead of a loose dict.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Union

from src.agents.llm import JsonLLM, LLMError
from src.agents.state import CaseState, Citation, Freshness, PolicyMatch, as_dict

logger = logging.getLogger(__name__)

SearchHit = Dict[str, Any]
SearchFn = Callable[[str], Union[Sequence[SearchHit], Awaitable[Sequence[SearchHit]]]]

DEFAULT_CONFIG: Dict[str, Dict[str, Any]] = {
    "query_expansion": {
        "system_prompt": "formulator_system_prompt.jinja",
        "max_tokens": 2048,
        "top_p": 0.85,
        "temperature": 0.7,
    },
    "evaluation": {
        # Legacy AgenticRAG judges with the formulator system prompt; keep that for parity.
        "system_prompt": "formulator_system_prompt.jinja",
        "max_tokens": 1500,
        "top_p": 0.9,
        "temperature": 0.65,
    },
}


def format_hits(hits: Sequence[SearchHit], truncate: int = 2000) -> str:
    """Render hits exactly like ``AgenticRAG._format_azure_search_results``."""
    blocks = []
    for hit in hits:
        content = hit.get("chunk") or "N/A"
        if len(content) > truncate:
            content = content[:truncate] + "..."
        blocks.append(
            "========================================\n"
            f"🆔 ID: {hit.get('chunk_id', 'N/A')}\n"
            f"📂 Source Doc Path: {hit.get('parent_path', 'N/A')}\n"
            f"📜 Content: {content}\n"
            f"💡 Caption: {hit.get('caption') or 'Caption not available'}\n"
            "========================================"
        )
    return "\n\n".join(blocks)


def make_azure_search_fn(
    search_client: Any,
    *,
    semantic_configuration_name: str = "my-semantic-config",
    vector_field: str = "vector",
    k_nearest_neighbors: int = 5,
    weight: float = 0.5,
    top: int = 5,
) -> SearchFn:
    """Hybrid + semantic Azure AI Search, same parameters as the legacy retriever."""
    from azure.search.documents.models import (
        QueryAnswerType,
        QueryCaptionType,
        QueryType,
        VectorizableTextQuery,
    )

    def search(query: str) -> List[SearchHit]:
        results = search_client.search(
            search_text=query,
            vector_queries=[
                VectorizableTextQuery(
                    text=query,
                    k_nearest_neighbors=k_nearest_neighbors,
                    fields=vector_field,
                    weight=weight,
                )
            ],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name=semantic_configuration_name,
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=top,
        )
        hits = []
        for r in results:
            captions = r.get("@search.captions") or []
            caption = None
            if captions:
                caption = captions[0].highlights or captions[0].text
            hits.append(
                {
                    "chunk_id": r.get("chunk_id"),
                    "parent_path": r.get("parent_path"),
                    "chunk": r.get("chunk"),
                    "caption": caption,
                    "score": r.get("@search.reranker_score"),
                    # Only populated if the index projects the blob's last-modified
                    # time (see docs/architecture/agentic-2026.md, data freshness).
                    "last_modified": r.get("last_modified")
                    or r.get("metadata_storage_last_modified"),
                }
            )
        return hits

    return search


def _default_prompts() -> Any:
    from src.pipeline.promptEngineering.prompt_manager import PromptManager

    return PromptManager()


def _clinical_prompt_args(clinical: Dict[str, Any]) -> Dict[str, Any]:
    treatment = clinical.get("treatment_request") or {}
    return {
        "diagnosis": clinical.get("diagnosis"),
        "medication_or_procedure": treatment.get("name_of_medication_or_procedure"),
        "code": treatment.get("code_of_medication_or_procedure"),
        "dosage": treatment.get("dosage"),
        "duration": treatment.get("duration"),
        "rationale": treatment.get("rationale"),
    }


class PolicyAgent:
    name = "policy_agent"

    def __init__(
        self,
        llm: JsonLLM,
        search: SearchFn,
        prompts: Any = None,
        config: Optional[Dict[str, Dict[str, Any]]] = None,
        max_attempts: int = 3,
    ) -> None:
        self.llm = llm
        self.search = search
        self.prompts = prompts or _default_prompts()
        self.config = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
        for key, value in (config or {}).items():
            self.config.setdefault(key, {}).update(value)
        self.max_attempts = max_attempts

    async def _search(self, query: str) -> List[SearchHit]:
        result = self.search(query)
        if hasattr(result, "__await__"):
            result = await result
        return list(result or [])

    async def expand(self, clinical: Dict[str, Any], feedback: List[str]) -> str:
        cfg = self.config["query_expansion"]
        user = self.prompts.get_prompt(
            "formulator_user_prompt.jinja", **_clinical_prompt_args(clinical)
        )
        if feedback:
            user += (
                "\n\nA previous search did not find a sufficient policy. Reviewer notes:\n- "
                + "\n- ".join(feedback)
                + "\nFormulate a different query that addresses these gaps."
            )
        out = await self.llm(
            system=self.prompts.get_prompt(cfg["system_prompt"]),
            user=user,
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            top_p=cfg["top_p"],
        )
        return str(out.get("optimized_query") or "").strip()

    async def judge(self, query: str, hits: Sequence[SearchHit]) -> Dict[str, Any]:
        cfg = self.config["evaluation"]
        out = await self.llm(
            system=self.prompts.get_prompt(cfg["system_prompt"]),
            user=self.prompts.get_prompt(
                "evaluator_user_prompt.jinja",
                query=query,
                SearchResults=format_hits(hits),
            ),
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            top_p=cfg["top_p"],
        )
        return {
            "policies": [str(p) for p in out.get("policies") or []],
            "reasoning": [str(r) for r in out.get("reasoning") or []],
            "retry": bool(out.get("retry", True)),
        }

    @staticmethod
    def _matches(
        approved: List[str], reasoning: List[str], hits: Sequence[SearchHit]
    ) -> List[PolicyMatch]:
        matches = []
        for url in approved:
            own = [h for h in hits if h.get("parent_path") == url]
            why = next((r for r in reasoning if url in r), None)
            modified = next(
                (h.get("last_modified") for h in own if h.get("last_modified")), None
            )
            freshness = (
                Freshness.from_value("policy", url, modified, "search.last_modified")
                if modified
                else Freshness.unknown(
                    "policy",
                    url,
                    note="Search index does not project the policy's last-modified date.",
                )
            )
            matches.append(
                PolicyMatch(
                    blob_url=url,
                    chunk_id=own[0].get("chunk_id") if own else None,
                    reasoning=why,
                    freshness=freshness,
                    score=max((h.get("score") or 0.0 for h in own), default=None)
                    if own
                    else None,
                    citations=[
                        Citation(
                            source=url,
                            chunk_id=h.get("chunk_id"),
                            quote=(h.get("caption") or (h.get("chunk") or "")[:280])
                            or None,
                        )
                        for h in own
                    ]
                    or [Citation(source=url)],
                )
            )
        return matches

    async def run(self, state: CaseState) -> CaseState:
        """Populate ``expanded_query``, ``policies`` and ``policy_search_reasoning``."""
        clinical = as_dict(state.clinical_information)
        feedback: List[str] = []
        for attempt in range(1, self.max_attempts + 1):
            try:
                query = await self.expand(clinical, feedback)
                if not query:
                    logger.warning("%s attempt %d: empty query", self.name, attempt)
                    continue
                hits = await self._search(query)
                if not hits:
                    feedback = [f"The query {query!r} returned no results."]
                    continue
                verdict = await self.judge(query, hits)
            except LLMError as exc:
                logger.warning("%s attempt %d failed: %s", self.name, attempt, exc)
                continue

            state.expanded_query = query
            state.policy_search_reasoning = verdict["reasoning"]
            if not verdict["retry"] and verdict["policies"]:
                state.policies = self._matches(
                    verdict["policies"], verdict["reasoning"], hits
                )
                return state
            feedback = verdict["reasoning"] or [f"No policy matched {query!r}."]

        logger.error("%s: no policy found after %d attempts", self.name, self.max_attempts)
        state.expanded_query = None
        state.policies = []
        return state
