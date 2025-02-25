import asyncio
import glob
import json
import logging
import os
from datetime import datetime
from typing import Union, List

from azure.ai.evaluation import evaluate

from src.aifoundry.aifoundry_helper import AIFoundryManager
from src.evals.case import Case, Evaluation
from src.evals.pipeline import PipelineEvaluator
from src.extractors.pdfhandler import OCRHelper
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.promptEngineering.models import PatientInformation, PhysicianInformation, ClinicalInformation


class ClinicalExtractorEvaluator(PipelineEvaluator):
    # The expected evaluator class name in the pipeline configuration.
    EXPECTED_PIPELINE = "src.pipeline.clinicalExtractor.evaluator.ClinicalExtractorEvaluator"

    def __init__(self, cases_dir: str, temp_dir: str = "./temp", logger=None):
        """
        Initialize the evaluator with:
          - cases_dir: Directory containing YAML test case definitions.
          - temp_dir: Directory for temporary file processing.
          - data_extractor: An instance that processes files and generates responses.

        The 'uploaded_files' value will be determined from the YAML pipeline configuration.
        """
        self.cases_dir = cases_dir
        self.cases = {}  # Mapping from case_id to Case instance.
        self.results = []  # For logging raw responses or evaluator outputs.
        self.global_evaluators = {}  # Evaluators from the pipeline-level configuration.
        self.ai_foundry_manager = AIFoundryManager()
        self.temp_dir = temp_dir
        self.data_extractor = ClinicalDataExtractor()
        self.uploaded_files = None  # Will be set from the YAML pipeline configuration.
        if logger is None:
            self.logger = logging.getLogger(__name__)
            if not self.logger.handlers:
                logging.basicConfig(level=logging.INFO)
        else:
            self.logger = logger

    async def generate_responses(self) -> dict:
        """
        Generates a response by processing the uploaded files.
        Uses the data extractor to process the files (after extracting images from PDFs)
        and returns a dictionary containing the OCR results along with timestamps.
        """
        dt_started = datetime.now().isoformat()
        image_files = self.process_uploaded_files(self.uploaded_files)
        try:
            result = await self.data_extractor.run(
                image_files=image_files,
                PatientInformation=PatientInformation,
                PhysicianInformation=PhysicianInformation,
                ClinicalInformation=ClinicalInformation,
            )
            extracted_results = {
                "ocr_results": {
                    "patient_information": result["patient_data"].model_dump(mode="json"),
                    "physician_information": result["physician_data"].model_dump(mode="json"),
                    "clinical_information": result["clinician_data"].model_dump(mode="json"),
                }
            }
            final_result = {
                "generated_output": extracted_results["ocr_results"],
                "dt_started": dt_started,
                "dt_completed": datetime.now().isoformat()
            }
            self.logger.info(f"Response generation completed: {final_result}")
            return final_result
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return {
                "generated_output": {},
                "dt_started": dt_started,
                "dt_completed": datetime.now().isoformat(),
                "error": str(e)
            }
        finally:
            self.cleanup_temp_dir()

    def process_uploaded_files(self, uploaded_files: Union[str, List[str]]) -> List[str]:
        """
        Processes the uploaded file(s) by extracting images from PDFs.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]
        ocr_helper = OCRHelper()
        image_files = []
        for file_path in uploaded_files:
            try:
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path,
                    output_path=self.temp_dir
                )
                self.logger.info(f"Extracted images from {file_path}: {output_paths}")
                image_files.extend(output_paths)
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")
        return image_files

    async def preprocess(self):
        """
        Preprocessing step:
          - Loads YAML test case definitions from the cases directory.
          - For each YAML file:
              * Loads and validates the pipeline configuration.
              * Sets the 'uploaded_files' value.
              * Instantiates evaluators on a per-case basis.
              * Processes each test case:
                  - Creates a Case instance.
                  - Runs OCR evaluation (via generate_responses) and creates Evaluation records.
        """
        case_files = glob.glob(os.path.join(self.cases_dir, "*.yaml"))
        for file_path in case_files:
            config = self._load_yaml(file_path)
            if not config:
                continue

            file_id = os.path.splitext(os.path.basename(file_path))[0]
            if file_id not in config:
                self.logger.warning(f"Expected root key '{file_id}' not found in {file_path}. Skipping.")
                continue

            root_obj = config[file_id]
            pipeline_config = self._get_pipeline_config(root_obj, file_path)
            if not pipeline_config:
                continue

            self.uploaded_files = pipeline_config.get("uploaded_files")
            if not self.uploaded_files:
                self.logger.warning(f"No 'uploaded_files' specified in pipeline config in {file_path}. Skipping.")
                continue

            # Instantiate global evaluators from the pipeline config.
            self.global_evaluators = self._instantiate_evaluators(root_obj)

            cases_list = root_obj.get("cases", [])
            if not cases_list:
                self.logger.warning(f"No cases found under root key '{file_id}' in {file_path}. Skipping.")
                continue

            for case_id in cases_list:
                if case_id not in config:
                    self.logger.warning(f"Test case '{case_id}' not found in file {file_path}. Skipping.")
                    continue

                test_case_obj = config[case_id]
                self.cases[case_id] = Case(case_name=case_id)

                # Instantiate evaluators for this test case.
                # Use test-case specific evaluators if defined; otherwise, fall back to global evaluators.
                if "evaluators" in test_case_obj:
                    case_evaluators = self._instantiate_evaluators(test_case_obj)
                else:
                    case_evaluators = self._instantiate_evaluators(root_obj)
                self.cases[case_id].evaluators = case_evaluators

                await self._process_ocr_evaluation(case_id, test_case_obj)

    async def _process_ocr_evaluation(self, case_id: str, test_case_obj: dict):
        """
        For a test case that requires OCR evaluation, run generate_responses() and create Evaluation records.
        """
        response = await self.generate_responses()
        generated_output = response.get("generated_output", {})
        flat_generated = self._flatten_dict(generated_output)
        evaluations_list = test_case_obj.get("evaluations", [])
        for eval_item in evaluations_list:
            query = eval_item.get("query")
            expected_val = eval_item.get("ground_truth")
            actual_val = flat_generated.get(query, "")
            evaluation_record = Evaluation(
                query=query,
                response=actual_val,
                ground_truth=expected_val,
                context=None,
                conversation=None,
                scores=None
            )
            self.cases[case_id].evaluations.append(evaluation_record)
            self.results.append({
                "case": case_id,
                "query": query,
                "ocr_response": actual_val
            })

    async def run_evaluations(self):
        """
        Evaluation step:
          - For each test case, creates an evaluation dataset and triggers the Azure AI evaluation.
          - Uses the evaluators stored on each Case object.
          - Stores the Azure evaluation results in each Case object.
        """
        git_hash = self._get_git_hash()
        for case_id, case_obj in self.cases.items():
            evaluators = getattr(case_obj, "evaluators", None)
            if evaluators is None:
                self.logger.warning(f"No evaluators set for case '{case_id}', skipping evaluation.")
                continue

            evaluator_config = {}
            # Build the column mapping for each evaluator.
            # "response" is always included, while "query", "ground_truth", and "context" are added
            # only if at least one evaluation in the case contains that attribute.
            for evaluator_name in evaluators.keys():
                column_mapping = {"response": "${data.response}"}
                optional_keys = ["query", "ground_truth", "context"]
                for key in optional_keys:
                    # Check if any evaluation object has the attribute and a non-None value.
                    if any(hasattr(eval_item, key) and getattr(eval_item, key) is not None for eval_item in case_obj.evaluations):
                        column_mapping[key] = "${data." + key + "}"
                evaluator_config[evaluator_name] = {
                    "column_mapping": column_mapping
                }

            with case_obj.create_evaluation_dataset() as dataset_path:
                azure_result = evaluate(
                    evaluation_name=f"{case_id}#{git_hash}",
                    data=dataset_path,
                    evaluators=evaluators,
                    evaluator_config=evaluator_config,
                    azure_ai_project=self.ai_foundry_manager.project_config,
                )
                case_obj.azure_eval_result = azure_result

    def post_processing(self) -> str:
        """
        Post-processing step: Summarizes results for each test case.
        Returns:
            A JSON string containing the summary and raw results.
        """
        summary = {"cases": []}
        for case_id, case_obj in self.cases.items():
            summary["cases"].append({
                "case": case_obj.case_name,
                "results": case_obj.azure_eval_result
            })
        return json.dumps(summary, indent=3)


if __name__ == "__main__":
    pipeline = ClinicalExtractorEvaluator(cases_dir="./evals/cases")
    try:
        summary = asyncio.run(pipeline.run_pipeline())
        print(summary)
    except Exception as e:
        import traceback

        formatted_tb = ''.join(traceback.format_tb(e.__traceback__))
        print(f"Pipeline failed: {e}, stack trace: {formatted_tb}")
        exit(1)