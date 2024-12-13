# auto_pa_determinator.py
import os
from typing import Any, Callable, List, Tuple, Optional
from colorama import Fore
from utils.ml_logging import get_logger

from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.prompt_manager import PromptManager

class AutoPADeterminator:
    """
    Generate the final determination (decision) for the Prior Authorization request.
    If system prompts are not provided, fallback to the prompt_manager for retrieval.
    """

    def __init__(
        self,
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        azure_openai_client_o1: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        max_tokens: int = 2048,
        top_p: float = 0.8,
        temperature: float = 0.7,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        SYSTEM_PROMPT_PRIOR_AUTH: Optional[str] = None,
        local: bool = False
    ) -> None:
        """
        Initialize the AutoPADeterminator.

        Args:
            azure_openai_client: AzureOpenAIManager for main LLM calls. If None, init from env.
            azure_openai_client_o1: AzureOpenAIManager for O1 model calls. If None, init from env.
            prompt_manager: PromptManager instance for prompt templates. If None, create a new one.
            max_tokens: Max tokens for LLM responses.
            top_p: top_p for LLM responses.
            temperature: Temperature for LLM responses.
            frequency_penalty: Frequency penalty for LLM responses.
            presence_penalty: Presence penalty for LLM responses.
            SYSTEM_PROMPT_PRIOR_AUTH: System prompt for final determination. If None, fetched from prompt_manager.
            local: Whether to operate in local/tracing mode.
        """
        self.logger = get_logger(
            name="PAProcessing - Auto Determination", level=10, tracing_enabled=local
        )

        if azure_openai_client is None:
            api_key = os.getenv("AZURE_OPENAI_KEY", None)
            if api_key is None:
                self.logger.warning("No AZURE_OPENAI_KEY found. AutoPADeterminator may fail.")
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        if azure_openai_client_o1 is None:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION_01", "2024-09-01-preview")
            azure_openai_client_o1 = AzureOpenAIManager(api_version=api_version)
        self.azure_openai_client_o1 = azure_openai_client_o1

        self.prompt_manager = prompt_manager or PromptManager()
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # Fallback to prompt_manager if not provided
        self.SYSTEM_PROMPT_PRIOR_AUTH = SYSTEM_PROMPT_PRIOR_AUTH or self.prompt_manager.get_prompt("prior_auth_system_prompt.jinja")

        self.local = local

    async def generate_final_determination(
        self,
        caseId: str,
        patient_info: Any,
        physician_info: Any,
        clinical_info: Any,
        policy_text: str,
        summarize_policy_callback: Callable[[str], Any],
        use_o1: bool = False
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
                        patient_info, physician_info, clinical_info, summarized_policy, use_o1_flag
                    )
                    api_response = await model_client.generate_chat_response_o1(
                        query=summarized_prompt,
                        conversation_history=[],
                        max_completion_tokens=15000,
                    )
                return api_response
            except Exception as e:
                self.logger.warning(f"{model_client.__class__.__name__} model generation failed: {str(e)}")
                raise e

        if use_o1:
            self.logger.info(Fore.CYAN + f"Using o1 model for final determination for {caseId}...")
            try:
                api_response_determination = await generate_response_with_model(self.azure_openai_client_o1, user_prompt_pa, use_o1)
            except Exception:
                self.logger.info(Fore.CYAN + f"Retrying with 4o model for final determination for {caseId}...")
                use_o1 = False

        if not use_o1:
            max_retries = 2
            for attempt in range(1, max_retries + 1):
                try:
                    self.logger.info(Fore.CYAN + f"Using 4o model for final determination, attempt {attempt} for {caseId}...")
                    api_response_determination = await self.azure_openai_client.generate_chat_response(
                        query=user_prompt_pa,
                        system_message_content=self.SYSTEM_PROMPT_PRIOR_AUTH,
                        conversation_history=[],
                        response_format="text",
                        max_tokens=self.max_tokens,
                        top_p=self.top_p,
                        temperature=self.temperature,
                        frequency_penalty=self.frequency_penalty,
                        presence_penalty=self.presence_penalty,
                    )
                    if api_response_determination == "maximum context length":
                        summarized_policy = await summarize_policy_callback(policy_text)
                        summarized_prompt = self.prompt_manager.create_prompt_pa(
                            patient_info, physician_info, clinical_info, summarized_policy, use_o1
                        )
                        api_response_determination = await self.azure_openai_client.generate_chat_response(
                            query=summarized_prompt,
                            system_message_content=self.SYSTEM_PROMPT_PRIOR_AUTH,
                            conversation_history=[],
                            response_format="text",
                            max_tokens=self.max_tokens,
                            top_p=self.top_p,
                            temperature=self.temperature,
                            frequency_penalty=self.frequency_penalty,
                            presence_penalty=self.presence_penalty,
                        )
                    break
                except Exception as e:
                    self.logger.warning(f"4o model generation failed on attempt {attempt}: {str(e)}")
                    if attempt < max_retries:
                        self.logger.info(Fore.CYAN + "Retrying 4o model for final determination...")
                    else:
                        self.logger.error(f"All retries for 4o model failed for {caseId}.")
                        raise e

        final_response = api_response_determination["response"]
        self.logger.info(Fore.MAGENTA + "\nFinal Determination:\n" + final_response)

        return final_response, api_response_determination.get("conversation_history", [])
