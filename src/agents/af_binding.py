"""Optional Microsoft Agent Framework binding.

Core agents depend only on the ``JsonLLM`` protocol, so they run on Python 3.10
without extra packages. Install ``requirements-agents.txt`` (Python >= 3.11) to run
the same agents through Agent Framework, which adds middleware, OpenTelemetry
spans, and the option to swap in any AF chat client (for example a Foundry
project client).

    llm = AFJsonLLM(JsonLLMChatClient(AOAIJsonLLM(manager)))
    agent = PolicyAgent(llm=llm, search=search_fn)
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from src.agents.llm import JsonLLM, LLMError, parse_json_object

try:
    from agent_framework import Agent, BaseChatClient, ChatResponse, Message, tool

    AF_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only without the extra installed
    Agent = BaseChatClient = ChatResponse = Message = tool = None  # type: ignore
    AF_AVAILABLE = False

_INSTALL_HINT = "agent-framework-core is not installed; pip install -r requirements-agents.txt (Python >= 3.11)."


def require_af() -> None:
    if not AF_AVAILABLE:
        raise ImportError(_INSTALL_HINT)


_PARAM_KEYS = ("max_tokens", "temperature", "top_p")

if AF_AVAILABLE:

    class JsonLLMChatClient(BaseChatClient):
        """AF chat client backed by an existing ``JsonLLM`` (e.g. ``AOAIJsonLLM``)."""

        def __init__(self, llm: JsonLLM, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self._llm = llm

        async def _inner_get_response(self, *, messages, stream, options, **kwargs):
            system = str(options.get("instructions") or "")
            user = "\n\n".join(m.text for m in messages if m.text)
            params = {k: options[k] for k in _PARAM_KEYS if options.get(k) is not None}
            result = await self._llm(system=system, user=user, **params)
            return ChatResponse(messages=[Message(role="assistant", contents=[json.dumps(result)])])

else:  # pragma: no cover

    class JsonLLMChatClient:  # type: ignore[no-redef]
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            require_af()


class AFJsonLLM:
    """``JsonLLM`` that routes every call through an AF ``Agent`` run."""

    def __init__(self, client: Any, name: str = "autoauth", tools: Optional[List[Any]] = None) -> None:
        require_af()
        self.client = client
        self.name = name
        self.tools = tools or []

    async def __call__(
        self, *, system: str, user: str, max_tokens: int = 2048, temperature: float = 0.2, top_p: float = 0.9
    ) -> Dict[str, Any]:
        agent = Agent(self.client, instructions=system, name=self.name, tools=self.tools or None)
        response = await agent.run(
            user, options={"max_tokens": max_tokens, "temperature": temperature, "top_p": top_p}
        )
        text = getattr(response, "text", None)
        if not text:
            raise LLMError(f"{self.name}: empty response from Agent Framework")
        return parse_json_object(text)


def make_policy_search_tool(search: Callable[[str], Any]) -> Any:
    """Expose policy search as an AF tool so a tool-calling model can drive retrieval."""
    require_af()

    @tool(name="search_policies", description="Hybrid search over indexed prior-authorization policies.")
    async def search_policies(query: str) -> str:
        result = search(query)
        if hasattr(result, "__await__"):
            result = await result
        return json.dumps(
            [{k: h.get(k) for k in ("chunk_id", "parent_path", "caption")} for h in result or []]
        )

    return search_policies
