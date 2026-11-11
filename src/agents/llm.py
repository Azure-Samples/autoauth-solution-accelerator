"""The one LLM seam every AutoAuth agent depends on.

Agents only need "send a system + user prompt, get a JSON object back". Keeping
that behind :class:`JsonLLM` lets the same agent run on the existing
``AzureOpenAIManager`` (default), on Microsoft Agent Framework
(:mod:`src.agents.af_binding`), or on a fake in unit tests.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Protocol, runtime_checkable


class LLMError(RuntimeError):
    """The model call failed or did not return a JSON object."""


class ContextLengthExceeded(LLMError):
    """The prompt did not fit the model context window."""


@runtime_checkable
class JsonLLM(Protocol):
    async def __call__(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> Dict[str, Any]: ...


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_object(raw: Any) -> Dict[str, Any]:
    """Coerce a model reply into a dict, tolerating ```json fences."""
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise LLMError(f"Expected a JSON object, got {type(raw).__name__}.")
    text = _FENCE.sub("", raw.strip())
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise LLMError(f"Model did not return JSON: {text[:200]!r}") from None
        try:
            value = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model did not return JSON: {text[:200]!r}") from exc
    if not isinstance(value, dict):
        raise LLMError("Model returned JSON that is not an object.")
    return value


class AOAIJsonLLM:
    """:class:`JsonLLM` over the repo's existing ``AzureOpenAIManager``."""

    def __init__(self, manager: Any, seed: Optional[int] = 42) -> None:
        self.manager = manager
        self.seed = seed

    async def __call__(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 2048,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> Dict[str, Any]:
        result = await self.manager.generate_chat_response(
            query=user,
            system_message_content=system,
            conversation_history=[],
            response_format="json_object",
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            seed=self.seed,
        )
        if result is None:
            raise LLMError("Azure OpenAI call failed (no response).")
        if result == "maximum context length":
            raise ContextLengthExceeded("Prompt exceeds the model context window.")
        return parse_json_object(result.get("response"))
