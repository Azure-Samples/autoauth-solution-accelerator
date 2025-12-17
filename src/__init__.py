"""Top-level package safeguards and compatibility helpers."""

from __future__ import annotations

import logging
import random
from typing import Callable, Iterator


def _ensure_otlp_backoff_generator() -> None:
    """Guarantee compatibility with promptflow's expected OTLP backoff helper."""

    try:
        from opentelemetry.exporter.otlp.proto.common import _internal as otlp_internal
    except Exception:  # pragma: no cover - optional dependency
        return

    if hasattr(otlp_internal, "_create_exp_backoff_generator"):
        return

    def _create_exp_backoff_generator(
        initial_backoff: float = 1.0,
        maximum_backoff: float = 120.0,
        multiplier: float = 1.6,
        jitter: float = 0.2,
    ) -> Iterator[float]:
        current = max(initial_backoff, 0.0)
        upper_bound = max(maximum_backoff, current)
        scale = multiplier if multiplier > 1 else 1.0

        while True:
            delta = 0.0
            if jitter > 0:
                delta = random.uniform(-current * jitter, current * jitter)

            next_delay = max(0.0, min(current + delta, upper_bound))
            yield next_delay

            current = min(current * scale, upper_bound)

    otlp_internal._create_exp_backoff_generator = _create_exp_backoff_generator


def _enable_aad_for_azure_evaluators() -> None:
    """Allow Azure AI Evaluation graders to authenticate with Entra ID tokens."""

    try:
        from azure.ai.evaluation._aoai import aoai_grader  # type: ignore[import]
        from azure.identity import DefaultAzureCredential, get_bearer_token_provider
        from openai import AzureOpenAI
    except Exception:  # pragma: no cover - optional dependency
        return

    if getattr(aoai_grader, "_aad_patch_applied", False):
        return

    logger = logging.getLogger(__name__)
    token_scope = "https://cognitiveservices.azure.com/.default"
    credential: DefaultAzureCredential | None = None
    token_provider = None

    def _get_token_provider() -> Callable[[], str] | None:
        nonlocal credential, token_provider
        if token_provider is None:
            credential = credential or DefaultAzureCredential()
            token_provider = get_bearer_token_provider(credential, token_scope)
        return token_provider

    original_validate = aoai_grader.AzureOpenAIGrader._validate_model_config
    original_get_client = aoai_grader.AzureOpenAIGrader.get_client
    default_version = getattr(aoai_grader, "DEFAULT_AOAI_API_VERSION", None)

    def _patched_validate(self) -> None:
        config = self._model_config
        if config.get("api_key"):
            original_validate(self)
            return
        if "azure_endpoint" in config and config.get("azure_deployment"):
            return
        original_validate(self)

    def _patched_get_client(self):
        config = self._model_config
        if config.get("api_key"):
            return original_get_client(self)
        if "azure_endpoint" not in config:
            return original_get_client(self)

        provider = config.get("_aad_token_provider")
        if provider is None:
            try:
                provider = _get_token_provider()
                config["_aad_token_provider"] = provider
            except Exception:  # pragma: no cover - optional dependency
                logger.exception(
                    "Failed to initialize DefaultAzureCredential for AzureOpenAIGrader."
                )
                return original_get_client(self)

        return AzureOpenAI(
            azure_endpoint=config["azure_endpoint"],
            azure_deployment=config.get("azure_deployment", ""),
            azure_ad_token_provider=provider,
            api_version=config.get("api_version") or default_version,
        )

    aoai_grader.AzureOpenAIGrader._validate_model_config = _patched_validate
    aoai_grader.AzureOpenAIGrader.get_client = _patched_get_client
    aoai_grader._aad_patch_applied = True


_ensure_otlp_backoff_generator()
_enable_aad_for_azure_evaluators()

__all__ = ["_ensure_otlp_backoff_generator", "_enable_aad_for_azure_evaluators"]
