# clinical_data_extractor.py
import asyncio
import os
from typing import Any, Dict, List, Optional, Type, Union
from pydantic import BaseModel, ValidationError
from colorama import Fore
from src.pipeline.utils import load_config

from utils.ml_logging import get_logger
from src.aoai.aoai_helper import AzureOpenAIManager
from src.pipeline.promptEngineering.prompt_manager import PromptManager


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
        config_file: str = "ClinicalExtractor\\settings.yaml",
        azure_openai_client: Optional[AzureOpenAIManager] = None,
        prompt_manager: Optional[PromptManager] = None,
        caseId: Optional[str] = None,
    ) -> None:
        """
        Initialize the ClinicalDataExtractor.

        Args:
            azure_openai_client: Optional AzureOpenAIManager instance. If None, initialized from environment.
            prompt_manager: Optional PromptManager instance. If None, a new one is created.
            
        """
        self.config = load_config(config_file)
        self.run_config = self.config.get("run", {})
        self.patient_extraction_conf = self.config.get("patient_extraction", {})
        self.physician_extraction_conf = self.config.get("physician_extraction", {})
        self.clinical_extraction_conf = self.config.get("clinical_extraction", {})
        self.caseId = caseId
        self.prefix = f"[caseID: {self.caseId}] " if self.caseId else ""


        self.logger = get_logger(name=self.run_config['logging']['name'], 
                                 level=self.run_config['logging']['level'], 
                                 tracing_enabled=self.run_config['logging']['enable_tracing'])

        if azure_openai_client is None:
            api_key = os.getenv("AZURE_OPENAI_KEY", None)
            if api_key is None:
                self.logger.warning("No AZURE_OPENAI_KEY found. ClinicalDataExtractor may fail.")
            azure_openai_client = AzureOpenAIManager(api_key=api_key)
        self.azure_openai_client = azure_openai_client

        self.prompt_manager = prompt_manager or PromptManager()
       

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
            self.logger.info(Fore.CYAN + f"{self.prefix}\nExtracting patient data...")

            # Use provided values or default to self attributes
            system_message_content = self.prompt_manager.get_prompt(self.patient_extraction_conf['system_prompt'])
            user_prompt = self.prompt_manager.get_prompt(self.patient_extraction_conf['user_prompt'])
            max_tokens = self.patient_extraction_conf['max_tokens'] 
            top_p = self.patient_extraction_conf['top_p']
            temperature = self.patient_extraction_conf['temperature']
            frequency_penalty = self.patient_extraction_conf['frequency_penalty']
            presence_penalty = self.patient_extraction_conf['presence_penalty']

            api_response_patient = (
                await self.azure_openai_client.generate_chat_response(
                    query=user_prompt,
                    system_message_content=system_message_content,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=max_tokens,
                    top_p=top_p,
                    temperature=temperature,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
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
            self.logger.info(Fore.CYAN + f"{self.prefix}\nExtracting physician data...")
            # Use provided values or default to self attributes
            system_message_content = self.prompt_manager.get_prompt(self.physician_extraction_conf['system_prompt'])
            user_prompt = self.prompt_manager.get_prompt(self.physician_extraction_conf['user_prompt'])
            max_tokens = self.physician_extraction_conf['max_tokens'] 
            top_p = self.physician_extraction_conf['top_p']
            temperature = self.physician_extraction_conf['temperature']
            frequency_penalty = self.physician_extraction_conf['frequency_penalty']
            presence_penalty = self.physician_extraction_conf['presence_penalty']

            api_response_physician = (
                await self.azure_openai_client.generate_chat_response(
                    query=user_prompt,
                    system_message_content=system_message_content,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=max_tokens,
                    top_p=top_p,
                    temperature=temperature,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
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
            self.logger.info(Fore.CYAN + f"{self.prefix}\nExtracting clinician data...")
            # Use provided values or default to self attributes
            system_message_content = self.prompt_manager.get_prompt(self.clinical_extraction_conf['system_prompt'])
            user_prompt = self.prompt_manager.get_prompt(self.clinical_extraction_conf['user_prompt'])
            max_tokens = self.clinical_extraction_conf['max_tokens'] 
            top_p = self.clinical_extraction_conf['top_p']
            temperature = self.clinical_extraction_conf['temperature']
            frequency_penalty = self.clinical_extraction_conf['frequency_penalty']
            presence_penalty = self.clinical_extraction_conf['presence_penalty']

            api_response_clinician = (
                await self.azure_openai_client.generate_chat_response(
                    query=user_prompt,
                    system_message_content=system_message_content,
                    image_paths=image_files,
                    conversation_history=[],
                    response_format="json_object",
                    max_tokens=max_tokens,
                    top_p=top_p,
                    temperature=temperature,
                    frequency_penalty=frequency_penalty,
                    presence_penalty=presence_penalty,
                )
            )
            validated_data = await self.validate_with_field_level_correction(
                api_response_clinician["response"], ClinicalInformation
            )
            return validated_data, api_response_clinician["conversation_history"]
        except Exception as e:
            self.logger.error(f"Error extracting clinician data: {e}")
            return None, []

    async def run(
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

            (patient_data, _), (physician_data, _), (clinician_data, _) = await asyncio.gather(
                patient_data_task, physician_data_task, clinician_data_task
            )

            return {
                "patient_data": patient_data,
                "physician_data": physician_data,
                "clinician_data": clinician_data,
            }
        except Exception as e:
            self.logger.error(f"Error extracting all data: {e}")
            return {
                "patient_data": None,
                "physician_data": None,
                "clinician_data": None,
            }
