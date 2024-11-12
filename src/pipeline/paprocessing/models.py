from typing import Optional
from pydantic import BaseModel, Field

class PhysicianContact(BaseModel):
    """
    Represents the contact information for a physician.
    """
    office_phone: str = Field(default="Not provided", alias="office_phone")
    fax: str = Field(default="Not provided", alias="fax")
    office_address: str = Field(default="Not provided", alias="office_address")

class PhysicianInformation(BaseModel):
    """
    Represents the information related to a physician.
    """
    physician_name: str = Field(default="Not provided", alias="physician_name")
    specialty: str = Field(default="Not provided", alias="specialty")
    physician_contact: PhysicianContact = Field(default_factory=PhysicianContact, alias="physician_contact")

class PatientInformation(BaseModel):
    """
    Represents the information related to a patient.
    """
    patient_name: str = Field(default="Not provided", alias="patient_name")
    patient_date_of_birth: str = Field(default="Not provided", alias="patient_date_of_birth")
    patient_id: str = Field(default="Not provided", alias="patient_id")
    patient_address: str = Field(default="Not provided", alias="patient_address")
    patient_phone_number: str = Field(default="Not provided", alias="patient_phone_number")

class TreatmentRequest(BaseModel):
    """
    Represents a request for a specific treatment or medication.
    """
    name_of_medication_or_procedure: str = Field(default="Not provided", alias="name_of_medication_or_procedure")
    code_of_medication_or_procedure: str = Field(default="Not provided", alias="code_of_medication_or_procedure")
    dosage: str = Field(default="Not provided", alias="dosage")
    duration: str = Field(default="Not provided", alias="duration")
    rationale: str = Field(default="Not provided", alias="rationale")
    presumed_eligibility: str = Field(default="Not provided", alias="presumed_eligibility")

class ClinicalInformation(BaseModel):
    """
    Represents the clinical information related to a patient's treatment.
    """
    diagnosis: str = Field(default="Not provided", alias="diagnosis")
    icd_10_code: str = Field(default="Not provided", alias="icd_10_code")
    prior_treatments_and_results: str = Field(default="Not provided", alias="prior_treatments_and_results")
    specific_drugs_taken_and_failures: str = Field(default="Not provided", alias="specific_drugs_taken_and_failures")
    alternative_drugs_required: str = Field(default="Not provided", alias="alternative_drugs_required")
    relevant_lab_results_or_imaging: str = Field(default="Not provided", alias="relevant_lab_results_or_imaging")
    symptom_severity_and_impact: str = Field(default="Not provided", alias="symptom_severity_and_impact")
    prognosis_and_risk_if_not_approved: str = Field(default="Not provided", alias="prognosis_and_risk_if_not_approved")
    clinical_rationale_for_urgency: str = Field(default="Not provided", alias="clinical_rationale_for_urgency")
    treatment_request: TreatmentRequest = Field(default_factory=TreatmentRequest, alias="treatment_request")