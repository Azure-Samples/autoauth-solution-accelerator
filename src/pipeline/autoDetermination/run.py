# TODO: Improve logic + Add docstrings and type hints
import os
from typing import Any, Callable, List, Optional, Tuple

from colorama import Fore

from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.promptEngineering.prompt_manager import PromptManager
from src.pipeline.utils import load_config
from src.utils.ml_logging import get_logger


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
            "4o_autoDetermination", {}
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
                    "No AZURE_OPENAI_KEY found. AutoPADeterminator will use EntraID."
                )
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        if azure_openai_client_o1 is None:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION_01", "2025-01-01-preview")
            azure_openai_client_o1 = AzureOpenAIManager(api_version=api_version)
        self.azure_openai_client_o1 = azure_openai_client_o1

        self.prompt_manager = prompt_manager or PromptManager()

    def _get_reasoning_model_settings(self) -> dict:
        """Return configuration for reasoning model (o1/o3), or empty if not set.

        Checks environment variables for reasoning deployment/model and pairs with
        configured max tokens. This prevents AttributeError when reasoning is
        requested but settings are absent.
        """
        deployment = os.getenv("AZURE_OPENAI_REASONING_DEPLOYMENT_ID") or os.getenv(
            "AZURE_OPENAI_REASONING_MODEL_ID"
        )
        if not deployment:
            return {}

        api_version = (
            os.getenv("AZURE_OPENAI_REASONING_API_VERSION")
            or os.getenv("AZURE_OPENAI_API_VERSION_01")
            or os.getenv("AZURE_OPENAI_API_VERSION")
            or "2025-03-01-preview"
        )

        return {
            "deployment": deployment,
            "alias": deployment,
            "api_version": api_version,
            "max_completion_tokens": self.o1_auto_determination_config.get(
                "max_completion_tokens", 15000
            ),
        }

    async def run(
        self,
        patient_info: Any = None,
        physician_info: Any = None,
        clinical_info: Any = None,
        policy_text: Optional[str] = None,
        summarize_policy_callback: Optional[Callable[[str], Any]] = None,
        use_reasoning: bool = False,
        caseId: Optional[str] = None,
        session_id: Optional[str] = None,
        policies: Optional[Any] = None,
        clinical_data: Optional[Any] = None,
        **_: Any,
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
            use_reasoning: Whether to attempt using the O1 model first.

        Returns:
            A tuple containing the final determination text and the conversation history.
        """
        resolved_case_id = caseId or session_id
        if resolved_case_id:
            self.caseId = resolved_case_id
            self.prefix = f"[caseID: {self.caseId}] "

        # Fallbacks when called from MAF workflow
        if clinical_data and not clinical_info:
            clinical_info = clinical_data
        if not patient_info:
            patient_info = clinical_info.get("patient_info", {}) if isinstance(clinical_info, dict) else {}
        if not physician_info:
            physician_info = clinical_info.get("physician_info", {}) if isinstance(clinical_info, dict) else {}

        # Convert dicts to Pydantic models for prompt manager
        from src.pipeline.promptEngineering.models import (
            PatientInformation,
            PhysicianInformation,
            ClinicalInformation,
        )
        # Handle None or empty clinical_info
        if clinical_info is None:
            clinical_info = {}
        if isinstance(patient_info, dict):
            patient_info = PatientInformation(**patient_info)
        if isinstance(physician_info, dict):
            physician_info = PhysicianInformation(**physician_info)
        if isinstance(clinical_info, dict):
            clinical_info = ClinicalInformation(**clinical_info)

        # Build policy text from policies list if not provided
        if policy_text is None and policies:
            try:
                policy_texts = []
                if isinstance(policies, list):
                    for p in policies:
                        if isinstance(p, dict):
                            policy_texts.append(p.get("content") or p.get("text") or "")
                        else:
                            policy_texts.append(str(p))
                else:
                    policy_texts.append(str(policies))
                policy_text = "\n\n".join([p for p in policy_texts if p]) or ""
            except Exception:
                policy_text = ""

        # Default summarizer if not provided
        if summarize_policy_callback is None:
            async def summarize_policy_callback(text: str) -> str:
                return text

        user_prompt_pa = self.prompt_manager.create_prompt_pa(
            patient_info, physician_info, clinical_info, policy_text, use_reasoning
        )

        # Normalize flag naming (use_reasoning == use_reasoning) for downstream calls
        use_reasoning = bool(use_reasoning)

        self.logger.info(Fore.CYAN + f"Generating final determination for {caseId}")
        self.logger.info(f"Input clinical information: {user_prompt_pa}")

        reasoning_getter = getattr(self, "_get_reasoning_model_settings", None)
        if callable(reasoning_getter):
            reasoning_settings = reasoning_getter()
        else:
            reasoning_settings = {}
            if use_reasoning:
                self.logger.warning(
                    "Reasoning model requested but _get_reasoning_model_settings is missing; falling back to GPT-4o."
                )
        model_client = self.azure_openai_client_o1

        async def generate_response_with_model(model_client, prompt, use_reasoning_flag):
            """Invoke the reasoning model with configured max tokens and deployment."""
            target_model = reasoning_settings.get("deployment")
            max_tokens_reasoning = reasoning_settings.get("max_completion_tokens", 15000)
            return await model_client.generate_chat_response_o1(
                query=prompt,
                conversation_history=[],
                max_completion_tokens=max_tokens_reasoning,
                model=target_model,
            )

        async def generate_reasoning_response(prompt: str) -> Any:
            if not reasoning_settings:
                raise RuntimeError(
                    "Reasoning model requested but not configured. Set AZURE_OPENAI_REASONING_MODEL_ID or AZURE_OPENAI_REASONING_DEPLOYMENT_ID."
                )

            try:
                api_response = await model_client.generate_chat_response_o1(
                    query=prompt,
                    conversation_history=[],
                    max_completion_tokens=reasoning_settings.get(
                        "max_completion_tokens", 15000
                    ),
                )
                if api_response == "maximum context length":
                    summarized_policy = await summarize_policy_callback(policy_text)
                    summarized_prompt = self.prompt_manager.create_prompt_pa(
                        patient_info,
                        physician_info,
                        clinical_info,
                        summarized_policy,
                        use_reasoning,
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

        reasoning_enabled = use_reasoning
        if reasoning_enabled and not reasoning_settings:
            self.logger.warning(
                "Reasoning model requested but neither AZURE_OPENAI_REASONING_MODEL_ID nor AZURE_OPENAI_REASONING_DEPLOYMENT_ID is configured. Falling back to GPT-4o."
            )
            reasoning_enabled = False

        api_response_determination = None

        if reasoning_enabled:
            self.logger.info(
                Fore.CYAN + f"Using o1 model for final determination for {caseId}..."
            )
            try:
                api_response_determination = await generate_response_with_model(
                    self.azure_openai_client_o1, user_prompt_pa, use_reasoning
                )
            except Exception:
                self.logger.info(
                    Fore.CYAN
                    + f"Retrying with 4o model for final determination for {caseId}..."
                )
                use_reasoning = False

        if not use_reasoning:
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(
                        Fore.CYAN
                        + f"Using 4o model for final determination, attempt {attempt} for {caseId}..."
                    )

                    # Use provided values or default to self attributes
                    system_message_content = self.prompt_manager.get_prompt(
                        self.four0_auto_determination_config["system_prompt"]
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
                            use_reasoning,
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
                        f"4o model generation failed on attempt {attempt}: {str(e)}",
                        exc_info=True,
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

        if api_response_determination is None:
            raise RuntimeError("Failed to generate determination response")

        final_response = api_response_determination.get("response", "")
        self.logger.info(Fore.MAGENTA + "\nFinal Determination:\n" + final_response)

        return final_response, api_response_determination.get(
            "conversation_history", []
        )
