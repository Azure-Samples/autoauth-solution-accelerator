"""
`aifoundry_helper.py` is a module for managing interactions with Azure AI Foundry within our application.
"""

import os
from typing import Optional

from azure.ai.inference.tracing import AIInferenceInstrumentor
from azure.ai.projects import AIProjectClient
from azure.core.settings import settings
from azure.identity import DefaultAzureCredential
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

from src.utils.ml_logging import get_logger


class AIFoundryManager:
    """
    A manager class for interacting with Azure AI Foundry.

    This class provides methods for initializing the AI Foundry project and setting up telemetry using OpenTelemetry.
    """

    def __init__(self, project_connection_string: Optional[str] = None):
        """
        Initializes the AIFoundryManager with the project connection string.

        Args:
            project_connection_string (Optional[str]): The connection string for the Azure AI Foundry project.
                If not provided, it will be fetched from the environment variable
                "AZURE_AI_FOUNDRY_CONNECTION_STRING".

        Raises:
            ValueError: If the project connection string is not provided.
        """
        self.logger = get_logger(
            name="AIFoundryManager", level=10, tracing_enabled=False
        )
        self.project_connection_string: str = project_connection_string or os.getenv(
            "AZURE_AI_FOUNDRY_CONNECTION_STRING"
        )
        self.project_client: Optional[AIProjectClient] = None
        self.project_config: Optional[dict] = None
        self._validate_configurations()
        self._initialize_project()

    def _validate_configurations(self) -> None:
        """
        Validates the necessary configurations for the AI Foundry Manager.

        Raises:
            ValueError: If any required configuration is missing.
        """
        if not self.project_connection_string:
            self.logger.error("AZURE_AI_FOUNDRY_CONNECTION_STRING is not set.")
            raise ValueError("AZURE_AI_FOUNDRY_CONNECTION_STRING is not set.")
        self.logger.info("Configuration validation successful.")

    def _initialize_project(self) -> None:
        """
        Initializes the AI Foundry project client and sets the project configuration.

        The connection string is expected to have the format:
            <endpoint>;<subscription_id>;<resource_group_name>;<project_name>
        For example:
            "eastus2.api.azureml.ms;28d2df62-e322-4b25-b581-c43b94bd2607;rg-priorauth-eastus2-hls-autoauth;evaluations"

        This method sets:
            self.project_config = {
                "subscription_id": <subscription_id>,
                "resource_group_name": <resource_group_name>,
                "project_name": <project_name>
            }

        Then, it initializes the AIProjectClient using the connection string and DefaultAzureCredential.

        Raises:
            Exception: If initialization fails or the connection string format is invalid.
        """
        try:
            # Parse the connection string.
            tokens = self.project_connection_string.split(";")
            if len(tokens) < 4:
                raise Exception(
                    "Invalid connection string format: expected at least 4 semicolon-separated tokens."
                )

            # tokens[0] is the endpoint (unused here),
            # tokens[1] is the subscription_id,
            # tokens[2] is the resource_group_name,
            # tokens[3] is the project_name.
            self.project_config = {
                "subscription_id": tokens[1],
                "resource_group_name": tokens[2],
                "project_name": tokens[3],
            }

            self.project_client = AIProjectClient.from_connection_string(
                conn_str=self.project_connection_string,
                credential=DefaultAzureCredential(),
            )
            self.logger.info("AIProjectClient initialized successfully.")
        except Exception as e:
            self.logger.error(f"Failed to initialize AIProjectClient: {e}")
            raise Exception(f"Failed to initialize AIProjectClient: {e}")

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

            HTTPXClientInstrumentor().instrument()
            self.logger.info("HTTPX instrumented for OpenTelemetry.")

        except Exception as e:
            self.logger.error(f"Failed to initialize telemetry: {e}")
            raise Exception(f"Failed to initialize telemetry: {e}")
