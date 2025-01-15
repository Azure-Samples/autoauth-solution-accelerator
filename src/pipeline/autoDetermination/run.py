# TODO: Improve logic + Add docstrings and type hints
import os
from typing import Any, Callable, List, Optional, Tuple

from colorama import Fore

from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.promptEngineering.prompt_manager import PromptManager
from src.pipeline.utils import load_config
from utils.ml_logging import get_logger


class AutoPADeterminator:
    """
    Generate the final determination (decision) for the Prior Authorization request.
    If system prompts are not provided, fallback to the prompt_manager for retrieval.
    """

    def __init__(
        self,
        config_file: str = os.path.join("autoDetermination", "settings.yaml"),
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        azure_openai_client_o1: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        caseId: Optional[str] = None,
    ) -> None:
        """
        Initialize the AutoPADeterminator.

        Args:
            azure_openai_client: AzureOpenAIManager for main LLM calls. If None, init from env.
            azure_openai_client_o1: AzureOpenAIManager for O1 model calls. If None, init from env.
            prompt_manager: PromptManager instance for prompt templates. If None, create a new one.
        """
        self.caseId = caseId
        self.prefix = f"[caseID: {self.caseId}] " if self.caseId else ""
        self.config = load_config(config_file)
        self.run_config = self.config.get("run", {})
        self.four0_auto_determination_config = self.run_config.get(
            "4o_auto_determination", {}
        )
        self.o1_auto_determination_config = self.run_config.get(
            "o1_autoDetermination", {}
        )

        self.logger = get_logger(
            name=self.run_config["logging"]["name"],
            level=self.run_config["logging"]["level"],
            tracing_enabled=self.run_config["logging"]["enable_tracing"],
        )

        if azure_openai_client is None:
            api_key = os.getenv("AZURE_OPENAI_KEY", None)
            if api_key is None:
                self.logger.warning(
                    "No AZURE_OPENAI_KEY found. AutoPADeterminator may fail."
                )
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        if azure_openai_client_o1 is None:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION_01", "2024-09-01-preview")
            azure_openai_client_o1 = AzureOpenAIManager(api_version=api_version)
        self.azure_openai_client_o1 = azure_openai_client_o1

        self.prompt_manager = prompt_manager or PromptManager()

    async def run(
        self,
        patient_info: Any,
        physician_info: Any,
        clinical_info: Any,
        policy_text: str,
        summarize_policy_callback: Callable[[str], Any],
        use_o1: bool = False,
        caseId: Optional[str] = None,
    ) -> Tuple[str, List[str]]:
        """
        Generate the final determination for the PA request. If maximum context length is exceeded,
        attempts to summarize the policy and retry.

        Args:
            caseId: The unique case identifier.
            patient_info: Patient data model.
            physician_info: Physician data model.
            clinical_info: Clinical data model.
            policy_text: The relevant policy text.
            summarize_policy_callback: Callback to summarize the policy if needed.
            use_o1: Whether to attempt using the O1 model first.

        Returns:
            A tuple containing the final determination text and the conversation history.
        """
        if caseId:
            self.caseId = caseId
            self.prefix = f"[caseID: {self.caseId}] "

        user_prompt_pa = self.prompt_manager.create_prompt_pa(
            patient_info, physician_info, clinical_info, policy_text, use_o1
        )

        self.logger.info(Fore.CYAN + f"Generating final determination for {caseId}")
        self.logger.info(f"Input clinical information: {user_prompt_pa}")

        async def generate_response_with_model(model_client, prompt, use_o1_flag):
            try:
                api_response = await model_client.generate_chat_response_o1(
                    query=prompt,
                    conversation_history=[],
                    max_completion_tokens=15000,
                )
                if api_response == "maximum context length":
                    summarized_policy = await summarize_policy_callback(policy_text)
                    summarized_prompt = self.prompt_manager.create_prompt_pa(
                        patient_info,
                        physician_info,
                        clinical_info,
                        summarized_policy,
                        use_o1_flag,
                    )
                    api_response = await model_client.generate_chat_response_o1(
                        query=summarized_prompt,
                        conversation_history=[],
                        max_completion_tokens=self.o1_auto_determination_config.get(
                            "max_completion_tokens", 15000
                        ),
                    )
                return api_response
            except Exception as e:
                self.logger.warning(
                    f"{model_client.__class__.__name__} model generation failed: {str(e)}"
                )
                raise e

        if use_o1:
            self.logger.info(
                Fore.CYAN + f"Using o1 model for final determination for {caseId}..."
            )
            try:
                api_response_determination = await generate_response_with_model(
                    self.azure_openai_client_o1, user_prompt_pa, use_o1
                )
            except Exception:
                self.logger.info(
                    Fore.CYAN
                    + f"Retrying with 4o model for final determination for {caseId}..."
                )
                use_o1 = False

        if not use_o1:
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(
                        Fore.CYAN
                        + f"Using 4o model for final determination, attempt {attempt} for {caseId}..."
                    )

                    # Use provided values or default to self attributes
                    system_message_content = (
                        system_message_content
                        or self.prompt_manager.get_prompt(
                            self.four0_auto_determination_config["system_prompt"]
                        )
                    )
                    max_tokens = self.four0_auto_determination_config["max_tokens"]
                    top_p = self.four0_auto_determination_config["top_p"]
                    temperature = self.four0_auto_determination_config["temperature"]
                    frequency_penalty = self.four0_auto_determination_config[
                        "frequency_penalty"
                    ]
                    presence_penalty = self.four0_auto_determination_config[
                        "presence_penalty"
                    ]

                    api_response_determination = (
                        await self.azure_openai_client.generate_chat_response(
                            query=user_prompt_pa,
                            system_message_content=system_message_content,
                            conversation_history=[],
                            response_format="text",
                            max_tokens=max_tokens,
                            top_p=top_p,
                            temperature=temperature,
                            frequency_penalty=frequency_penalty,
                            presence_penalty=presence_penalty,
                        )
                    )
                    if api_response_determination == "maximum context length":
                        summarized_policy = await summarize_policy_callback(policy_text)
                        summarized_prompt = self.prompt_manager.create_prompt_pa(
                            patient_info,
                            physician_info,
                            clinical_info,
                            summarized_policy,
                            use_o1,
                        )
                        api_response_determination = (
                            await self.azure_openai_client.generate_chat_response(
                                query=summarized_prompt,
                                system_message_content=system_message_content,
                                conversation_history=[],
                                response_format="text",
                                max_tokens=max_tokens,
                                top_p=top_p,
                                temperature=temperature,
                                frequency_penalty=frequency_penalty,
                                presence_penalty=presence_penalty,
                            )
                        )
                    break
                except Exception as e:
                    self.logger.warning(
                        f"4o model generation failed on attempt {attempt}: {str(e)}"
                    )
                    if attempt < max_retries:
                        self.logger.info(
                            Fore.CYAN + "Retrying 4o model for final determination..."
                        )
                    else:
                        self.logger.error(
                            f"All retries for 4o model failed for {caseId}."
                        )
                        raise e

        final_response = api_response_determination["response"]
        self.logger.info(Fore.MAGENTA + "\nFinal Determination:\n" + final_response)

        return final_response, api_response_determination.get(
            "conversation_history", []
        )
