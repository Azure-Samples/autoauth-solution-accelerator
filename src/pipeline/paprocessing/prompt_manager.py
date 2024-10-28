from jinja2 import Environment, FileSystemLoader
import os
from typing import Dict, Any
from utils.ml_logging import get_logger

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
        
        print(f"Template directory resolved to: {template_path}")
        
        self.env = Environment(
            loader=FileSystemLoader(searchpath=template_path),
            autoescape=False
        )

        # Optional: List templates found for debugging
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

    def create_prompt_query_expansion(self, results: Dict[str, Any]) -> str:
        """
        Create a prompt for query expansion based on the given results.

        Args:
            results (Dict[str, Any]): The results dictionary containing clinical information.

        Returns:
            str: The rendered query expansion prompt.
        """
        clinical_information = results.get("Clinical Information", "Not provided")
        return self.get_prompt(
            'query_expansion_user_prompt.jinja',
            clinical_information=clinical_information
        )

    def create_prompt_pa(self, results: Dict[str, Any], policy_text: str) -> str:
        """
        Create a prompt for prior authorization based on the given results and policy text.

        Args:
            results (Dict[str, Any]): The results dictionary containing patient and clinical information.
            policy_text (str): The policy text to include in the prompt.

        Returns:
            str: The rendered prior authorization prompt.
        """
        patient_info = results.get("Patient Information", {})
        clinical_info = results.get("Clinical Information", {})
        plan_info = clinical_info.get("Plan for Treatment or Request for Prior Authorization", {})

        return self.get_prompt(
            'prior_auth_user_prompt.jinja',
            patient_name=patient_info.get("Patient Name", "Not provided"),
            patient_dob=patient_info.get("Patient Date of Birth", "Not provided"),
            patient_id=patient_info.get("Patient ID", "Not provided"),
            patient_address=patient_info.get("Patient Address", "Not provided"),
            patient_phone=patient_info.get("Patient Phone Number", "Not provided"),
            diagnosis=clinical_info.get("Diagnosis and medical justification (including ICD-10 code)", "Not provided"),
            treatment_history=clinical_info.get("Detailed history of alternative treatments and results", "Not provided"),
            lab_results=clinical_info.get("Relevant lab results or diagnostic imaging", "Not provided"),
            symptom_severity=clinical_info.get("Documented symptom severity and impact on daily life", "Not provided"),
            prognosis=clinical_info.get("Prognosis and risk if treatment is not approved", "Not provided"),
            urgency_rationale=clinical_info.get("Clinical rationale for urgency (if applicable)", "Not provided"),
            medication_or_procedure=plan_info.get("Medication or Procedure", "Not provided"),
            code=plan_info.get("Code", "Not provided"),
            dosage=plan_info.get("Dosage", "Not provided"),
            duration=plan_info.get("Duration", "Not provided"),
            rationale=plan_info.get("Rationale", "Not provided"),
            policy_text=policy_text
        )