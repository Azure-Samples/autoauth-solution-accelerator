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
        clinical_info = results.get("Clinical Information", {})
        plan_info = clinical_info.get("Plan for Treatment or Request for Prior Authorization", {})
        return self.get_prompt(
            'query_expansion_user_prompt.jinja',
            diagnosis=clinical_info.get("Diagnosis", "Not provided"),
            medication_or_procedure=plan_info.get("Name of the Medication or Procedure Being Requested", "Not provided"),
            code=plan_info.get("Code of the Medication or Procedure", "Not provided"),
            dosage=plan_info.get("Dosage or Plan for the Medication or Procedure", "Not provided"),
            duration=plan_info.get("Duration of Doses or Days of Treatment", "Not provided"),
            rationale=plan_info.get("Rationale for the Medication or Procedure", "Not provided"),
        )

    def create_prompt_pa(self, results: Dict[str, Any], policy_text: str, use_o1: bool = False) -> str:
        """
        Create a prompt for prior authorization based on the given results and policy text.
    
        Args:
            results (Dict[str, Any]): The results dictionary containing patient, physician, and clinical information.
            policy_text (str): The policy text to include in the prompt.
            use_o1 (bool): Indicates whether to use the o1 model. Defaults to False.
    
        Returns:
            str: The rendered prior authorization prompt.
        """
        patient_info = results['patient_data'].get("Patient Information", {})
        physician_info = results['physician_data'].get("Physician Information", {})
        clinical_info = results['clinician_data'].get("Clinical Information", {})
        plan_info = clinical_info.get("Plan for Treatment or Request for Prior Authorization", {})
    
        # Extracting Patient Information
        patient_name = patient_info.get("Patient Name", "Not provided")
        patient_dob = patient_info.get("Patient Date of Birth", "Not provided")
        patient_id = patient_info.get("Patient ID", "Not provided")
        patient_address = patient_info.get("Patient Address", "Not provided")
        patient_phone = patient_info.get("Patient Phone Number", "Not provided")
    
        # Extracting Physician Information
        physician_name = physician_info.get("Physician Name", "Not provided")
        specialty = physician_info.get("Specialty", "Not provided")
        physician_contact = physician_info.get("Physician Contact", {})
        physician_phone = physician_contact.get("Office Phone", "Not provided")
        physician_fax = physician_contact.get("Fax", "Not provided")
        physician_address = physician_contact.get("Office Address", "Not provided")
    
        # Extracting Clinical Information
        diagnosis = clinical_info.get("Diagnosis", "Not provided")
        icd10_code = clinical_info.get("ICD-10 Code", "Not provided")
        prior_treatments = clinical_info.get("Detailed History of Prior Treatments and Results", "Not provided")
        specific_drugs = clinical_info.get("Specific Drugs Already Taken by the Patient and if the Patient Failed These Prior Treatments", "Not provided")
        alternative_drugs_required = clinical_info.get("Alternative Drugs Required by the Specific PA Form", "Not provided")
        lab_results = clinical_info.get("Relevant Lab Results or Diagnostic Imaging", "Not provided")
        symptom_severity = clinical_info.get("Documented Symptom Severity and Impact on Daily Life", "Not provided")
        prognosis_risk = clinical_info.get("Prognosis and Risk if Treatment Is Not Approved", "Not provided")
        urgency_rationale = clinical_info.get("Clinical Rationale for Urgency (if applicable)", "Not provided")
    
        # Extracting Plan for Treatment
        requested_medication = plan_info.get("Name of the Medication or Procedure Being Requested", "Not provided")
        medication_code = plan_info.get("Code of the Medication or Procedure", "Not provided")
        dosage = plan_info.get("Dosage", "Not provided")
        duration = plan_info.get("Duration", "Not provided")
        medication_rationale = plan_info.get("Rationale", "Not provided")
        presumed_eligibility = plan_info.get("Presumed eligibility for the medication based on answers to the PA form questions", "Not provided")
    
        # Choose the appropriate template based on the use_o1 flag
        template_name = 'prior_auth_o1_user_prompt.jinja' if use_o1 else 'prior_auth_user_prompt.jinja'
    
        return self.get_prompt(
            template_name,
            # Patient Information
            patient_name=patient_name,
            patient_dob=patient_dob,
            patient_id=patient_id,
            patient_address=patient_address,
            patient_phone=patient_phone,
            # Physician Information
            physician_name=physician_name,
            specialty=specialty,
            physician_phone=physician_phone,
            physician_fax=physician_fax,
            physician_address=physician_address,
            # Clinical Information
            diagnosis=diagnosis,
            icd10_code=icd10_code,
            prior_treatments=prior_treatments,
            specific_drugs=specific_drugs,
            alternative_drugs_required=alternative_drugs_required,
            lab_results=lab_results,
            symptom_severity=symptom_severity,
            prognosis_risk=prognosis_risk,
            urgency_rationale=urgency_rationale,
            # Plan for Treatment or Request for Prior Authorization
            requested_medication=requested_medication,
            medication_code=medication_code,
            dosage=dosage,
            treatment=duration,
            medication_rationale=medication_rationale,
            presumed_eligibility=presumed_eligibility,
            # Policy Text
            policy_text=policy_text
        )