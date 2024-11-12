from jinja2 import Environment, FileSystemLoader
import os
from typing import Any
from utils.ml_logging import get_logger
from pydantic import BaseModel

logger = get_logger()

class PromptManager:
    def __init__(self, template_dir: str = 'templates'):
        """
        Initialize the PromptManager with the given template directory.

        Args:
            template_dir (str): The directory containing the Jinja2 templates.
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(current_dir, template_dir)
        
        self.env = Environment(
            loader=FileSystemLoader(searchpath=template_path),
            autoescape=False
        )

        templates = self.env.list_templates()
        print(f"Templates found: {templates}")

    def get_prompt(self, template_name: str, **kwargs) -> str:
        """
        Render a template with the given context.

        Args:
            template_name (str): The name of the template file.
            **kwargs: The context variables to render the template with.

        Returns:
            str: The rendered template as a string.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            raise ValueError(f"Error rendering template '{template_name}': {e}")

    def create_prompt_query_expansion(self, clinical_info: BaseModel) -> str:
        """
        Create a prompt for query expansion using clinical information.

        Args:
            clinical_info (BaseModel): A model instance containing clinical information.

        Returns:
            str: The rendered query expansion prompt.
        """
        return self.get_prompt(
            'query_expansion_user_prompt.jinja',
            diagnosis=clinical_info.diagnosis,
            medication_or_procedure=clinical_info.treatment_request.name_of_medication_or_procedure,
            code=clinical_info.treatment_request.code_of_medication_or_procedure,
            dosage=clinical_info.treatment_request.dosage,
            duration=clinical_info.treatment_request.duration,
            rationale=clinical_info.treatment_request.rationale
        )

    def create_prompt_pa(self, patient_info: BaseModel, physician_info: BaseModel, 
                         clinical_info: BaseModel, policy_text: str, use_o1: bool = False) -> str:
        """
        Create a prompt for prior authorization based on patient, physician, clinical information, and policy text.

        Args:
            patient_info (BaseModel): A model instance for patient information.
            physician_info (BaseModel): A model instance for physician information.
            clinical_info (BaseModel): A model instance for clinical information.
            policy_text (str): The policy text to include in the prompt.
            use_o1 (bool): Indicates whether to use the o1 model. Defaults to False.

        Returns:
            str: The rendered prior authorization prompt.
        """
        template_name = 'prior_auth_o1_user_prompt.jinja' if use_o1 else 'prior_auth_user_prompt.jinja'
        
        return self.get_prompt(
            template_name,
            # Patient Information
            patient_name=patient_info.patient_name,
            patient_dob=patient_info.patient_date_of_birth,
            patient_id=patient_info.patient_id,
            patient_address=patient_info.patient_address,
            patient_phone=patient_info.patient_phone_number,
            # Physician Information
            physician_name=physician_info.physician_name,
            specialty=physician_info.specialty,
            physician_phone=physician_info.physician_contact.office_phone,
            physician_fax=physician_info.physician_contact.fax,
            physician_address=physician_info.physician_contact.office_address,
            # Clinical Information
            diagnosis=clinical_info.diagnosis,
            icd10_code=clinical_info.icd_10_code,
            prior_treatments=clinical_info.prior_treatments_and_results,
            specific_drugs=clinical_info.specific_drugs_taken_and_failures,
            alternative_drugs_required=clinical_info.alternative_drugs_required,
            lab_results=clinical_info.relevant_lab_results_or_imaging,
            symptom_severity=clinical_info.symptom_severity_and_impact,
            prognosis_risk=clinical_info.prognosis_and_risk_if_not_approved,
            urgency_rationale=clinical_info.clinical_rationale_for_urgency,
            # Plan for Treatment
            requested_medication=clinical_info.treatment_request.name_of_medication_or_procedure,
            medication_code=clinical_info.treatment_request.code_of_medication_or_procedure,
            dosage=clinical_info.treatment_request.dosage,
            treatment_duration=clinical_info.treatment_request.duration,
            medication_rationale=clinical_info.treatment_request.rationale,
            presumed_eligibility=clinical_info.treatment_request.presumed_eligibility,
            # Policy Text
            policy_text=policy_text
        )
