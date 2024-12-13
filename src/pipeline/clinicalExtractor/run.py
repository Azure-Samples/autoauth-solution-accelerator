# clinical_data_extractor.py
import asyncio
import os
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError
from colorama import Fore

from utils.ml_logging import get_logger
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.prompt_manager import PromptManager


class ClinicalDataExtractor:
    """
    Extract clinical data (patient, physician, and clinician) from provided image files using
    LLM-based Named Entity Recognition (NER) prompts and Pydantic validation.

    This class:
    - Accepts optional parameters for prompts. If not provided, it falls back to 'prompt_manager' to retrieve them.
    - Uses 'azure_openai_client' for LLM calls.
    - Logs its activity using a configured logger.
    """

    def __init__(
        self,
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        max_tokens: int = 2048,
        top_p: float = 0.8,
        temperature: float = 0.7,
        frequency_penalty: float = 0.0,
        presence_penalty: float = 0.0,
        PATIENT_PROMPT_NER_SYSTEM: Optional[str] = None,
        PHYSICIAN_PROMPT_NER_SYSTEM: Optional[str] = None,
        CLINICIAN_PROMPT_NER_SYSTEM: Optional[str] = None,
        PATIENT_PROMPT_NER_USER: Optional[str] = None,
        PHYSICIAN_PROMPT_NER_USER: Optional[str] = None,
        CLINICIAN_PROMPT_NER_USER: Optional[str] = None,
        local: bool = False
    ) -> None:
        """
        Initialize the ClinicalDataExtractor.

        Args:
            azure_openai_client: Optional AzureOpenAIManager instance. If None, initialized from environment.
            prompt_manager: Optional PromptManager instance. If None, a new one is created.
            max_tokens: Maximum tokens for LLM responses.
            top_p: top_p value for LLM sampling.
            temperature: Temperature for LLM sampling.
            frequency_penalty: Frequency penalty for LLM responses.
            presence_penalty: Presence penalty for LLM responses.
            PATIENT_PROMPT_NER_SYSTEM: System prompt for patient NER. If None, fetched from prompt_manager.
            PHYSICIAN_PROMPT_NER_SYSTEM: System prompt for physician NER. If None, fetched from prompt_manager.
            CLINICIAN_PROMPT_NER_SYSTEM: System prompt for clinician NER. If None, fetched from prompt_manager.
            PATIENT_PROMPT_NER_USER: User prompt for patient NER. If None, fetched from prompt_manager.
            PHYSICIAN_PROMPT_NER_USER: User prompt for physician NER. If None, fetched from prompt_manager.
            CLINICIAN_PROMPT_NER_USER: User prompt for clinician NER. If None, fetched from prompt_manager.
            local: Whether to enable local/tracing logging mode.
        """
        self.logger = get_logger(
            name="ClinicalDataExtractor", level=10, tracing_enabled=local
        )

        if azure_openai_client is None:
            api_key = os.getenv("AZURE_OPENAI_KEY", None)
            if api_key is None:
                self.logger.warning("No AZURE_OPENAI_KEY found. ClinicalDataExtractor may fail.")
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        self.prompt_manager = prompt_manager or PromptManager()

        self.max_tokens = max_tokens
        self.top_p = top_p
        self.temperature = temperature
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty

        # Fall back to prompt_manager if prompts not provided
        self.PATIENT_PROMPT_NER_SYSTEM = PATIENT_PROMPT_NER_SYSTEM or self.prompt_manager.get_prompt("ner_patient_system.jinja")
        self.PHYSICIAN_PROMPT_NER_SYSTEM = PHYSICIAN_PROMPT_NER_SYSTEM or self.prompt_manager.get_prompt("ner_physician_system.jinja")
        self.CLINICIAN_PROMPT_NER_SYSTEM = CLINICIAN_PROMPT_NER_SYSTEM or self.prompt_manager.get_prompt("ner_clinician_system.jinja")
        self.PATIENT_PROMPT_NER_USER = PATIENT_PROMPT_NER_USER or self.prompt_manager.get_prompt("ner_patient_user.jinja")
        self.PHYSICIAN_PROMPT_NER_USER = PHYSICIAN_PROMPT_NER_USER or self.prompt_manager.get_prompt("ner_physician_user.jinja")
        self.CLINICIAN_PROMPT_NER_USER = CLINICIAN_PROMPT_NER_USER or self.prompt_manager.get_prompt("ner_clinician_user.jinja")

        self.local = local

    async def validate_with_field_level_correction(
        self, data: Dict[str, Any], model_class: Type[BaseModel]
    ) -> BaseModel:
        """
        Validate a dictionary against a Pydantic model. If validation fails for a field, assign a default value.

        Args:
            data: The dictionary containing the extracted fields.
            model_class: The Pydantic model class to validate against.

        Returns:
            A validated Pydantic model instance with corrected fields if necessary.
        """
        validated_data: Dict[str, Any] = {}
        for field_name, model_field in model_class.model_fields.items():
            expected_alias = model_field.alias or field_name
            value = data.get(expected_alias, None)

            try:
                validated_instance = model_class(**{field_name: value})
                validated_data[field_name] = getattr(validated_instance, field_name)
            except ValidationError as e:
                self.logger.warning(f"Validation error for '{expected_alias}': {e}")
                if model_field.default is not None:
                    default_value = model_field.default
                elif model_field.default_factory is not None:
                    default_value = model_field.default_factory()
                else:
                    field_type = model_field.outer_type_
                    if field_type == str:
                        default_value = "Not provided"
                    elif field_type == int:
                        default_value = 0
                    elif field_type == float:
                        default_value = 0.0
                    elif field_type == bool:
                        default_value = False
                    elif field_type == list:
                        default_value = []
                    elif field_type == dict:
                        default_value = {}
                    else:
                        default_value = None
                validated_data[field_name] = default_value

        instance = model_class(**validated_data)
        return instance

    async def extract_patient_data(
        self, image_files: List[str], PatientInformation: Type[BaseModel]
    ) -> Union[Optional[BaseModel], List[str]]:
        """
        Extract patient data from the provided image files.

        Args:
            image_files: A list of image file paths extracted from PDFs.
            PatientInformation: The Pydantic model for validating patient data.

        Returns:
            A tuple containing the validated patient data model and the conversation history.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting patient data...")
            api_response_patient = (
                await self.azure_openai_client.generate_chat_response(
                    query=self.PATIENT_PROMPT_NER_USER,
                    system_message_content=self.PATIENT_PROMPT_NER_SYSTEM,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    temperature=self.temperature,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                )
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_patient["response"], PatientInformation
            )
            return validated_data, api_response_patient["conversation_history"]
        except Exception as e:
            self.logger.error(f"Error extracting patient data: {e}")
            return None, []

    async def extract_physician_data(
        self, image_files: List[str], PhysicianInformation: Type[BaseModel]
    ) -> Union[Optional[BaseModel], List[str]]:
        """
        Extract physician data from the provided image files.

        Args:
            image_files: A list of image file paths.
            PhysicianInformation: The Pydantic model for validating physician data.

        Returns:
            A tuple containing the validated physician data model and the conversation history.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting physician data...")
            api_response_physician = (
                await self.azure_openai_client.generate_chat_response(
                    query=self.PHYSICIAN_PROMPT_NER_USER,
                    system_message_content=self.PHYSICIAN_PROMPT_NER_SYSTEM,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    temperature=self.temperature,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                )
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_physician["response"], PhysicianInformation
            )
            return validated_data, api_response_physician["conversation_history"]
        except Exception as e:
            self.logger.error(f"Error extracting physician data: {e}")
            return None, []

    async def extract_clinician_data(
        self, image_files: List[str], ClinicalInformation: Type[BaseModel]
    ) -> Union[Optional[BaseModel], List[str]]:
        """
        Extract clinician data from the provided image files.

        Args:
            image_files: A list of image file paths.
            ClinicalInformation: The Pydantic model for validating clinical information.

        Returns:
            A tuple containing the validated clinical data model and the conversation history.
        """
        try:
            self.logger.info(Fore.CYAN + "\nExtracting clinician data...")
            api_response_clinician = (
                await self.azure_openai_client.generate_chat_response(
                    query=self.CLINICIAN_PROMPT_NER_USER,
                    system_message_content=self.CLINICIAN_PROMPT_NER_SYSTEM,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=self.max_tokens,
                    top_p=self.top_p,
                    temperature=self.temperature,
                    frequency_penalty=self.frequency_penalty,
                    presence_penalty=self.presence_penalty,
                )
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_clinician["response"], ClinicalInformation
            )
            return validated_data, api_response_clinician["conversation_history"]
        except Exception as e:
            self.logger.error(f"Error extracting clinician data: {e}")
            return None, []

    async def extract_all_data(
        self,
        image_files: List[str],
        PatientInformation: Type[BaseModel],
        PhysicianInformation: Type[BaseModel],
        ClinicalInformation: Type[BaseModel]
    ) -> Dict[str, Any]:
        """
        Extract patient, physician, and clinical data concurrently.

        Args:
            image_files: A list of image file paths extracted from PDFs.
            PatientInformation: Pydantic model for patient data.
            PhysicianInformation: Pydantic model for physician data.
            ClinicalInformation: Pydantic model for clinical data.

        Returns:
            A dictionary containing patient, physician, and clinician data along with their conversation histories.
        """
        try:
            patient_data_task = self.extract_patient_data(image_files, PatientInformation)
            physician_data_task = self.extract_physician_data(image_files, PhysicianInformation)
            clinician_data_task = self.extract_clinician_data(image_files, ClinicalInformation)

            (patient_data, patient_hist), (physician_data, phys_hist), (clinician_data, clin_hist) = await asyncio.gather(
                patient_data_task, physician_data_task, clinician_data_task
            )

            return {
                "patient_data": patient_data,
                "patient_conv_history": patient_hist,
                "physician_data": physician_data,
                "physician_conv_history": phys_hist,
                "clinician_data": clinician_data,
                "clinician_conv_history": clin_hist,
            }
        except Exception as e:
            self.logger.error(f"Error extracting all data: {e}")
            return {
                "patient_data": None,
                "patient_conv_history": [],
                "physician_data": None,
                "physician_conv_history": [],
                "clinician_data": None,
                "clinician_conv_history": [],
            }
