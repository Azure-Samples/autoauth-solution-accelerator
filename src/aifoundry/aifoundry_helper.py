"""Utility helpers for interacting with Azure AI Foundry projects."""

import os
from typing import Any, Dict, Optional

from azure.ai.inference.tracing import AIInferenceInstrumentor
from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential
from azure.core.settings import settings
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor

try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:  # pragma: no cover - optional dependency
    HTTPXClientInstrumentor = None

from src.utils.ml_logging import get_logger


class AIFoundryManager:
    """Manage Azure AI Foundry project access, telemetry, and evaluations."""

    def __init__(
        self,
        project_connection_string: Optional[str] = None,
        project_endpoint: Optional[str] = None,
        credential: Optional[TokenCredential] = None,
    ) -> None:
        self.logger = get_logger(
            name="AIFoundryManager", level=10, tracing_enabled=False
        )
        self.project_connection_string = project_connection_string or os.getenv(
            "AZURE_AI_FOUNDRY_CONNECTION_STRING"
        )
        self.project_endpoint = project_endpoint or os.getenv(
            "AZURE_AI_PROJECT_ENDPOINT"
        )
        self.credential = DefaultAzureCredential()
        self.project_client: Optional[AIProjectClient] = None
        self.project_config: Optional[Dict[str, str]] = None
        self.azure_ai_project_scope: Optional[str] = None
        self._validate_configurations()
        self._initialize_project()

    def _validate_configurations(self) -> None:
        if not self.project_connection_string and not self.project_endpoint:
            message = "Either AZURE_AI_FOUNDRY_CONNECTION_STRING or AZURE_AI_PROJECT_ENDPOINT must be set."
            self.logger.error(message)
            raise ValueError(message)
        self.logger.info("Configuration validation successful.")

    def _initialize_project(self) -> None:
        try:
            # if self.project_connection_string:
            #     self._configure_from_connection_string()

            # if self.project_endpoint:
            #     self.azure_ai_project_scope = self._normalize_project_scope(
            #         self.project_endpoint
            #     )

            if self.project_connection_string and not self.project_endpoint:
                client = AIProjectClient.from_connection_string(
                    conn_str=self.project_connection_string,
                    credential=self.credential,
                )
                self.project_client = client
                derived_endpoint = self._extract_endpoint_from_client(client)
                if derived_endpoint:
                    self.project_endpoint = derived_endpoint
                    self.azure_ai_project_scope = derived_endpoint
            elif self.project_endpoint:
                self.project_client = AIProjectClient(
                    endpoint=self.project_endpoint,
                    credential=self.credential,
                )

            if not self.project_client:
                raise RuntimeError("Unable to initialize AIProjectClient.")

            if self.azure_ai_project_scope is None and self.project_endpoint:
                self.azure_ai_project_scope = self._normalize_project_scope(
                    self.project_endpoint
                )

            if self.project_config is None:
                self.project_config = {}

            if self.project_endpoint:
                self.project_config.setdefault("endpoint", self.project_endpoint)
            if self.azure_ai_project_scope:
                self.project_config.setdefault(
                    "project_scope", self.azure_ai_project_scope
                )

            self.logger.info("AIProjectClient initialized successfully.")
        except Exception as exc:  # pragma: no cover - defensive logging path
            self.logger.error(f"Failed to initialize AIProjectClient: {exc}")
            raise

    def _configure_from_connection_string(self) -> None:
        tokens = self.project_connection_string.split(";")
        if len(tokens) < 4:
            raise ValueError(
                "Invalid connection string format: expected '<endpoint>;<subscription_id>;<resource_group_name>;<project_name>'."
            )

        endpoint_hint, subscription_id, resource_group_name, project_name = tokens[:4]
        self.project_config = {
            "subscription_id": subscription_id,
            "resource_group_name": resource_group_name,
            "project_name": project_name,
        }

        if not self.project_endpoint:
            derived_endpoint = self._derive_project_endpoint(
                endpoint_hint, project_name
            )
            if derived_endpoint:
                self.project_endpoint = derived_endpoint

    def _derive_project_endpoint(
        self, endpoint_hint: str, project_name: str
    ) -> Optional[str]:
        base_endpoint = endpoint_hint.strip().rstrip("/")
        if not base_endpoint:
            return None

        if not base_endpoint.startswith("http"):
            base_endpoint = f"https://{base_endpoint}"

        if "/api/projects" in base_endpoint:
            if base_endpoint.endswith(project_name):
                return base_endpoint
            return f"{base_endpoint.rstrip('/')}/{project_name}"

        return f"{base_endpoint}/api/projects/{project_name}"

    def _normalize_project_scope(self, endpoint: str) -> str:
        scope = endpoint.rstrip("/")
        if "/api/projects" not in scope:
            scope = f"{scope}/api/projects"
        return scope

    def _extract_endpoint_from_client(self, client: AIProjectClient) -> Optional[str]:
        for attr in ("endpoint", "_endpoint", "_config"):
            value = getattr(client, attr, None)
            if isinstance(value, str) and value:
                return value.rstrip("/")
            if attr == "_config" and value is not None:
                candidate = getattr(value, "endpoint", None)
                if isinstance(candidate, str) and candidate:
                    return candidate.rstrip("/")
        return None

    def get_project_scope(self) -> Optional[str]:
        return self.azure_ai_project_scope

    def initialize_telemetry(self) -> None:
        """
        Sets up telemetry for the AI Foundry project using OpenTelemetry.

        Raises:
            Exception: If telemetry initialization fails.
        """
        if not self.project_client:
            self.logger.error(
                "AIProjectClient is not initialized. Call initialize_project() first."
            )
            raise Exception(
                "AIProjectClient is not initialized. Call initialize_project() first."
            )

        try:
            settings.tracing_implementation = "opentelemetry"
            self.logger.info("Tracing implementation set to OpenTelemetry.")

            # Instrument AI Inference API to enable tracing
            AIInferenceInstrumentor().instrument()
            self.logger.info("AI Inference API instrumented for tracing.")

            # Retrieve the Application Insights connection string from your AI project
            application_insights_connection_string = (
                self.project_client.telemetry.get_connection_string()
            )

            if application_insights_connection_string:
                configure_azure_monitor(
                    connection_string=application_insights_connection_string
                )
                self.logger.info("Azure Monitor configured for Application Insights.")
            else:
                self.logger.error(
                    "Application Insights is not enabled for this project."
                )
                raise Exception("Application Insights is not enabled for this project.")

            if HTTPXClientInstrumentor is not None:
                HTTPXClientInstrumentor().instrument()
                self.logger.info("HTTPX instrumented for OpenTelemetry.")
            else:
                self.logger.warning(
                    "HTTPX instrumentation is unavailable. Install 'opentelemetry-instrumentation-httpx' to enable it."
                )

        except Exception as e:
            self.logger.error(f"Failed to initialize telemetry: {e}")
            raise Exception(f"Failed to initialize telemetry: {e}")

    def run_local_evaluation(
        self,
        *,
        evaluation_name: str,
        data: Any,
        evaluators: Dict[str, Any],
        evaluator_config: Optional[Dict[str, Any]] = None,
        log_to_project: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Execute an evaluation locally with optional Azure AI project logging."""
        from azure.ai.evaluation import evaluate

        evaluate_kwargs = {
            "evaluation_name": evaluation_name,
            "data": data,
            "evaluators": evaluators,
        }

        if evaluator_config is not None:
            evaluate_kwargs["evaluator_config"] = evaluator_config

        if log_to_project:
            azure_project = self._build_azure_project_payload()
            if azure_project:
                evaluate_kwargs["azure_ai_project"] = azure_project
            else:
                self.logger.warning(
                    "Azure AI project logging requested but no project configuration is available."
                )

        evaluate_kwargs.update(kwargs)
        return evaluate(**evaluate_kwargs)

    def submit_cloud_evaluation(self, evaluation, **kwargs):
        """Submit an evaluation job to Azure AI Foundry for remote execution."""
        if not self.project_client:
            raise RuntimeError("AIProjectClient is not initialized.")

        evaluations_client = getattr(self.project_client, "evaluations", None)
        if evaluations_client is None:
            raise RuntimeError(
                "Evaluations client is not available on AIProjectClient."
            )

        for method_name in (
            "begin_create_or_update",
            "begin_create",
            "create",
        ):
            create_method = getattr(evaluations_client, method_name, None)
            if create_method:
                return create_method(evaluation=evaluation, **kwargs)

        raise RuntimeError("No supported method to submit evaluation jobs was found.")

    def _build_azure_project_payload(self) -> Optional[Dict[str, str]]:
        if not self.project_config:
            return None

        required_keys = ("subscription_id", "resource_group_name", "project_name")
        if all(self.project_config.get(key) for key in required_keys):
            return {key: self.project_config[key] for key in required_keys}

        payload: Dict[str, str] = {}
        endpoint = self.project_config.get("endpoint") or self.project_endpoint
        project_scope = (
            self.project_config.get("project_scope") or self.azure_ai_project_scope
        )

        if endpoint:
            payload["endpoint"] = endpoint
        if project_scope:
            payload["project_scope"] = project_scope

        return payload or None
