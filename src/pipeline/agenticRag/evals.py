import asyncio
import sys

from src.pipeline.agenticRag.run import AgenticRAG
from src.pipeline.promptEngineering.models import ClinicalInformation, TreatmentRequest

CASE_ID = "TEST-001"
agenticrag = AgenticRAG(caseId=CASE_ID)

my_clinical_info = ClinicalInformation(
    diagnosis="Crohn's Disease; Anemia 2/2 blood loss",
    icd_10_code="K50.90; D50.9",
    prior_treatments_and_results="Not provided",
    specific_drugs_taken_and_failures="Not provided",
    alternative_drugs_required="Not provided",
    relevant_lab_results_or_imaging=(
        "EGD Findings: Biopsies obtained and pending, Esophagus: Normal appearance, "
        "Stomach: Gastritis, erythema present, Duodenum: Mild to moderate duodenitis with edema; "
        "Colonoscopy Findings: Biopsies obtained and pending, Ileum: Patchy inflammation with areas of erythema and ulceration, "
        "Colon: Diffuse inflammation, Granularity and friability present, Rectum: Mild inflammation, no significant ulceration; "
        "MRI enterography: pending; CBC with Differential: Hemoglobin 9.0 g/dL, Hematocrit 32%, Red Blood Cells (RBC) 3.5 million/μL, "
        "Mean Corpuscular Volume (MCV) 78 fL, Mean Corpuscular Hemoglobin (MCH) 28 pg, Mean Corpuscular Hemoglobin Concentration (MCHC) 34 g/dL, "
        "Platelets 450,000 cells/μL, White Blood Cells (WBC) 12,000 cells/μL, Bands (Immature Neutrophils) 5%, Neutrophils 75%, "
        "Lymphocytes 18%, Monocytes 4%, Eosinophils 1%, Basophils 0%; CMP: Glucose 90 mg/dL, BUN 15 mg/dL, Creatinine 0.5 mg/dL, "
        "Sodium 138 mEq/L, Potassium 4.0 mEq/L, Chloride 102 mEq/L, Bicarbonate 24 mEq/L, Calcium 9.2 mg/dL; ESR 15 mm/h; CRP 12 mg/L; "
        "Fecal Calprotectin 100 μg/g; Fecal Occult Blood Positive; Liver Function Test: AST 25 U/L, ALT 22 U/L, ALP 120 U/L, "
        "Bilirubin (Total) 0.6 mg/dL; Iron Panel: Ferritin 15 ng/mL, Iron 40 μg/dL, Total Iron Binding Capacity (TIBC) 450 μg/dL; "
        "Folate Level 5 ng/mL; Vitamin B12 Level 300 pg/mL"
    ),
    symptom_severity_and_impact=(
        "Patient has multiple episodes of abdominal cramping and bowel movements with visible hematochezia, "
        "did not sleep well, appears pale, tired but interactive; Positive for fatigue, pallor, abdominal pain, "
        "hematochezia, dizziness, blood loss (by rectum); HR 110 bpm, BP 110/70 mmHg, RR 20 bpm, Temp 98.6°F (37°C); "
        "Pallor present, mild tachycardia present"
    ),
    prognosis_and_risk_if_not_approved=(
        "Patient continues to have frequent blood in stools and anemia as well as abdominal discomfort"
    ),
    clinical_rationale_for_urgency=(
        "Urgent (In checking this box, I attest to the fact that applying the standard review time frame "
        "may seriously jeopardize the customer's life, health, or ability to regain maximum function)"
    ),
    treatment_request=TreatmentRequest(
        name_of_medication_or_procedure="Adalimumab",
        code_of_medication_or_procedure="Not provided",
        dosage=(
            "160 mg (given as four 40 mg injections on day 1) followed by "
            "80 mg (given as two 40 mg injections) two weeks later. "
            "40 mg every other week starting 2 weeks from end dose"
        ),
        duration="6 months; 16 injections",
        rationale="Patient will likely need to initiate biologic therapy given severity of symptoms",
        presumed_eligibility="Not provided",
    ),
)

negative_clinical_info = ClinicalInformation(
    diagnosis="Common Cold",
    icd_10_code="J00",
    prior_treatments_and_results="Rest and hydration",
    specific_drugs_taken_and_failures="None",
    alternative_drugs_required="None",
    relevant_lab_results_or_imaging="None",
    symptom_severity_and_impact="Mild symptoms, no significant impact",
    prognosis_and_risk_if_not_approved="Symptoms will resolve on their own",
    clinical_rationale_for_urgency="None",
    treatment_request=TreatmentRequest(
        name_of_medication_or_procedure="Vitamin C",
        code_of_medication_or_procedure="Not provided",
        dosage="500 mg daily",
        duration="1 week",
        rationale="Support immune system",
        presumed_eligibility="Not provided",
    ),
)


async def test_agenticrag_run():
    try:
        result = await agenticrag.run(clinical_info=my_clinical_info, max_retries=3)
        print("E2E Test Result:", result)

        query = result.get("query")
        policies = result.get("policies", [])
        evaluation = result.get("evaluation")

        print(f"Query: {query}")
        print(f"Policies: {policies}")
        print(f"Evaluation: {evaluation}")

        expected_policies = [
            "https://storageaeastusfactory.blob.core.windows.net/pre-auth-policies/policies_ocr/001.pdf"
        ]

        assert (
            policies == expected_policies
        ), f"Unexpected policies: {policies}, expected: {expected_policies}"
        print("E2E Positive Test Passed!")
    except AssertionError as e:
        print("E2E Positive Test Failed:", e)
        sys.exit(1)
    except Exception as e:
        print("An error occurred during the test:", e)
        sys.exit(1)


async def test_agenticrag_run_negative():
    try:
        result = await agenticrag.run(
            clinical_info=negative_clinical_info, max_retries=3
        )
        print("Negative Test Result:", result)

        query = result.get("query")
        policies = result.get("policies", [])
        evaluation = result.get("evaluation")

        print(f"Query: {query}")
        print(f"Policies: {policies}")
        print(f"Evaluation: {evaluation}")

        expected_policies = []

        assert (
            policies == expected_policies
        ), f"Unexpected policies: {policies}, expected: {expected_policies}"
        print("E2E Negative Test Passed!")
    except AssertionError as e:
        print("E2E Negative Test Failed:", e)
        sys.exit(1)
    except Exception as e:
        print("An error occurred during the test:", e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_agenticrag_run())
    asyncio.run(test_agenticrag_run_negative())