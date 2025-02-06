import logging
import os
from typing import List, Literal, Optional

from pydantic import Field, PrivateAttr
from semantic_kernel import Kernel
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
)
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.connectors.ai.prompt_execution_settings import (
    PromptExecutionSettings,
)

from src.agenticai.skills import Skills
from src.utils.ml_logging import get_logger


class Agent(ChatCompletionAgent):
    """
    A custom chat completion agent integrating Azure OpenAI services and configurable plugins.

    This agent:
    - Integrates with Azure OpenAI Chat Completion services.
    - Allows specification of execution settings and function choice behaviors.
    - Dynamically loads specified plugins (skills) using the Skills manager.
    - Provides comprehensive logging and tracing capabilities.

    The agent is designed to be efficient, scalable, and memory-conscious.
    """

    skills: Optional[
        List[Literal["retrieval", "main", "rewriting", "evaluation"]]
    ] = Field(
        default=None, description="List of allowed plugin names to load as skills."
    )
    tracing_enabled: bool = Field(
        default=False, description="Flag to enable or disable tracing."
    )
    _logger: logging.Logger = PrivateAttr()
    _skills_manager: Skills = PrivateAttr(default=None)

    def __init__(
        self,
        service_id: Optional[str] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        skills: Optional[
            List[Literal["retrieval", "main", "rewriting", "evaluation"]]
        ] = None,
        execution_settings: Optional[PromptExecutionSettings] = None,
        function_choice_behavior: Optional[FunctionChoiceBehavior] = None,
        tracing_enabled: bool = False,
    ) -> None:
        """
        Initialize the CustomAgent with optional parameters for service configuration, instructions, skills,
        and execution behavior.

        :param service_id: The service ID for the agent.
        :param name: The name of the agent.
        :param id: The ID of the agent.
        :param description: The description of the agent.
        :param instructions: The instructions for the agent.
        :param skills: (optional) List of plugin names (skills) to load.
        :param execution_settings: (optional) Execution settings for the agent.
        :param function_choice_behavior: (optional) Function selection behavior.
        :param tracing_enabled: (optional) Flag to enable or disable tracing.
        :raises ValueError: If required environment variables for Azure OpenAI are missing.
        :raises FileNotFoundError: If specified plugin directories do not exist.
        """
        kernel = self._create_kernel_with_chat_completion(service_id)
        updated_execution_settings = self._configure_execution_settings(
            execution_settings, service_id, function_choice_behavior
        )

        super().__init__(
            service_id=service_id,
            kernel=kernel,
            name=name,
            id=id,
            description=description,
            instructions=instructions,
            execution_settings=updated_execution_settings,
        )

        self.skills = skills
        self.tracing_enabled = tracing_enabled
        self._model_post_init__()

    def _model_post_init__(self) -> None:
        """
        Post-initialization hook to finalize the model setup.

        :return: None
        :raises FileNotFoundError: If a specified skill directory does not exist.
        """
        self._logger = get_logger(
            name=f"CustomAgent-{self.name}" if self.name else "CustomAgent",
            level=10,
            tracing_enabled=self.tracing_enabled,
        )
        self._logger.debug("CustomAgent fully initialized.")
        if self.skills:
            PLUGIN_STORE = os.path.abspath("src/agenticai/plugins/plugins_store")
            self._skills_manager = Skills(parent_directory=PLUGIN_STORE)
            self._load_skills(self.skills)

    def _create_kernel_with_chat_completion(self, service_id: Optional[str]) -> Kernel:
        """
        Create and configure a Kernel instance with Azure Chat Completion services.

        :param service_id: The service ID for the agent.
        :return: A configured Kernel instance.
        :raises ValueError: If any required environment variable is missing.
        """
        deployment_name = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID")
        api_key = os.getenv("AZURE_OPENAI_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        try:
            if not all([deployment_name, api_key, endpoint, api_version]):
                missing_vars = [
                    var_name
                    for var_name, var_value in {
                        "AZURE_OPENAI_CHAT_DEPLOYMENT_ID": deployment_name,
                        "AZURE_OPENAI_KEY": api_key,
                        "AZURE_OPENAI_ENDPOINT": endpoint,
                        "AZURE_OPENAI_API_VERSION": api_version,
                    }.items()
                    if not var_value
                ]
                raise ValueError(
                    f"Missing environment variables: {', '.join(missing_vars)}"
                )

            kernel = Kernel()
            kernel.add_service(
                AzureChatCompletion(
                    service_id=service_id,
                    deployment_name=deployment_name,
                    api_key=api_key,
                    endpoint=endpoint,
                    api_version=api_version,
                )
            )
            return kernel
        except ValueError as e:
            logging.getLogger(__name__).error(
                "Failed to create kernel with Azure Chat Completion.", exc_info=True
            )
            raise e

    def _configure_execution_settings(
        self,
        user_settings: Optional[PromptExecutionSettings],
        service_id: Optional[str],
        function_choice_behavior: Optional[FunctionChoiceBehavior],
    ) -> OpenAIChatPromptExecutionSettings:
        """
        Configure execution settings, applying user settings or defaults if none are provided.

        :param user_settings: Optional user-provided execution settings.
        :param service_id: The service ID for the agent.
        :param function_choice_behavior: (optional) The function choice behavior.
        :return: An OpenAIChatPromptExecutionSettings instance.
        """
        try:
            if user_settings:
                if not isinstance(user_settings, OpenAIChatPromptExecutionSettings):
                    # If user_settings is provided but not the correct type, convert it.
                    new_settings = OpenAIChatPromptExecutionSettings(
                        service_id=service_id,
                        temperature=user_settings.extension_data.get(
                            "temperature", 0.0
                        ),
                        max_tokens=user_settings.extension_data.get("max_tokens", 2000),
                        top_p=user_settings.extension_data.get("top_p", 0.8),
                        function_choice_behavior=function_choice_behavior
                        or user_settings.function_choice_behavior,
                    )
                    return new_settings
                else:
                    if function_choice_behavior:
                        user_settings.function_choice_behavior = (
                            function_choice_behavior
                        )
                    return user_settings

            # If no user_settings provided, create a new OpenAIChatPromptExecutionSettings
            return OpenAIChatPromptExecutionSettings(
                service_id=service_id,
                temperature=0.0,
                max_tokens=2000,
                top_p=0.8,
                function_choice_behavior=function_choice_behavior
                or FunctionChoiceBehavior.Auto(),
            )
        except Exception as e:
            logging.getLogger(__name__).error(
                "Failed to configure execution settings.", exc_info=True
            )
            raise e

    def _load_skills(
        self, skills: List[Literal["retrieval", "main", "rewriting", "evaluation"]]
    ) -> None:
        """
        Load the specified plugin skills using the Skills manager and integrate them into the kernel.

        :param skills: List of plugin names to load.
        :return: None
        :raises FileNotFoundError: If a specified skill directory does not exist.
        """

        self._skills_manager.load_skills(skills)

        for skill_name in skills:
            plugin = self._skills_manager.get_skill(skill_name)
            plugin_path = plugin.directory
            parent = os.path.dirname(plugin_path)
            name = os.path.basename(plugin_path)
            try:
                self.kernel.add_plugin(parent_directory=parent, plugin_name=name)
                self._logger.info("Successfully integrated plugin: %s", skill_name)
            except Exception as e:
                self._logger.error(
                    "Failed to integrate plugin: %s", skill_name, exc_info=True
                )
                raise e
