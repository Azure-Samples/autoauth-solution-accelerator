import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Union

from src.extractors.pdfhandler import OCRHelper
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.promptEngineering.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.utils.ml_logging import get_logger
from src.evals.custom.base_evaluator import BaseEvaluator  # Import the base evaluator
from rapidfuzz import fuzz
import asyncio


class OCRNEREvaluator(BaseEvaluator):
    def __init__(self, args: Dict[str, Any]):
        """
        Initialize the OCRNEREvaluation with parameters from YAML.

        Args:
            args: Dictionary of arguments (from the YAML "args" section)
                  containing keys such as 'uploaded_files', 'expected_output',
                  and 'similarity_threshold'.
        """
        super().__init__(args)
        # Required arguments for this evaluator
        self.uploaded_files = args["uploaded_files"]
        self.expected_output = args["expected_output"]
        # Expect "similarity_threshold" to be provided in the args dict.
        if "similarity_threshold" not in args:
            raise ValueError("Missing required argument: similarity_threshold")
        self.similarity_threshold = args["similarity_threshold"]

        self.data_extractor = ClinicalDataExtractor()
        self.logger = get_logger()
        self.temp_dir = "tempClinicalExtractor"

    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Allows the evaluator to be called as a function.

        This wraps the asynchronous run() method and returns a JSON-like dictionary
        with keys such as 'extracted_output', 'evaluations', 'pass', and timestamps.

        Returns:
            A dictionary containing the evaluation results.
        """
        try:
            # asyncio.run will execute the async run method and return the result.
            result = asyncio.run(self.run())
            return result
        except Exception as e:
            self.logger.error(f"Error during __call__: {e}")
            return {
                "extracted_output": None,
                "evaluations": {},
                "pass": False,
                "dt_started": None,
                "error": str(e)
            }

    def cleanup_temp_dir(self) -> None:
        """
        Clean up the temporary directory used for processing files.
        """
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"Failed to clean up temporary directory '{self.temp_dir}': {e}")

    def process_uploaded_files(self, uploaded_files: Union[str, List[str]]) -> List[str]:
        """
        Process uploaded files by extracting images from PDFs using OCR.

        Args:
            uploaded_files: A file path or list of file paths representing the uploaded PDFs.

        Returns:
            A list of extracted image file paths.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]

        # Initialize OCRHelper with no arguments.
        ocr_helper = OCRHelper()
        image_files = []
        for file_path in uploaded_files:
            try:
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=self.temp_dir
                )
                self.logger.info(f"Extracted images from {file_path}: {output_paths}")
                image_files.extend(output_paths)
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")
        return image_files

    async def run(self) -> Dict[str, Any]:
        """
        Execute the OCR/NER evaluation.

        This method:
          1. Processes the uploaded files to extract images.
          2. Runs the clinical data extraction pipeline.
          3. Compares the extracted output against the expected output.
          4. Returns a dictionary with the results and evaluation metrics.

        Returns:
            Dictionary containing the extracted output, similarity evaluation,
            and additional metadata.
        """
        dt_started = datetime.now().isoformat()
        image_files = self.process_uploaded_files(self.uploaded_files)

        try:
            # Run the clinical data extraction pipeline asynchronously.
            result = await self.data_extractor.run(
                image_files=image_files,
                PatientInformation=PatientInformation,
                PhysicianInformation=PhysicianInformation,
                ClinicalInformation=ClinicalInformation,
            )
            extracted_results = {
                "ocr_ner_results": {
                    "patient_info": result["patient_data"].model_dump(mode="json"),
                    "physician_info": result["physician_data"].model_dump(mode="json"),
                    "clinical_info": result["clinician_data"].model_dump(mode="json"),
                }
            }
            evaluation = self.evaluate_similarity(
                extracted=extracted_results["ocr_ner_results"],
                expected=self.expected_output["ocr_ner_results"]
            )

            final_result = {
                "evaluations": evaluation["evaluations"],
                "pass": evaluation["pass"],
                "dt_started": dt_started,
                "dt_completed": datetime.now().isoformat(),
            }
            self.logger.info(f"Evaluation completed: {final_result}")
            return final_result

        except Exception as e:
            self.logger.error(f"Error during evaluation: {e}")
            return {
                "evaluations": {},
                "pass": False,
                "dt_started": dt_started,
                "dt_completed": datetime.now().isoformat(),
            }
        finally:
            self.cleanup_temp_dir()

    def evaluate_similarity(self, extracted: Dict[str, Any], expected: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate similarity scores between extracted and expected data using the provided similarity_threshold.

        For each key, if the expected value is a dictionary, compare recursively. For other types,
        compute the similarity score using fuzz.ratio and place it under a "metrics" key in the detailed comparison.

        Args:
            extracted: Dictionary containing the extracted data.
            expected: Dictionary containing the expected data.

        Returns:
            A dictionary with:
                - "metrics": a dictionary of similarity scores (or nested dictionaries of scores),
                - "evaluations": a list of detailed comparison entries,
                - "pass": a boolean indicating if all similarity scores meet the threshold.
        """
        metrics = {}
        detailed_comparison = []

        for key, expected_value in expected.items():
            if isinstance(expected_value, dict) and isinstance(extracted.get(key), dict):
                # Recursive comparison for nested dictionaries.
                nested = self.evaluate_similarity(extracted.get(key, {}), expected_value)
                metrics[key] = nested["metrics"]
                detailed_comparison.extend(nested["evaluations"])
            else:
                extracted_value = extracted.get(key, "")
                try:
                    score = fuzz.ratio(str(extracted_value), str(expected_value))
                except Exception as e:
                    self.logger.error(f"Error calculating similarity for key '{key}': {e}")
                    score = 0
                metrics[key] = score
                detailed_comparison.append({
                    "key": key,
                    "extracted_value": extracted_value,
                    "expected_value": expected_value,
                    "metrics": {
                        "similarity_score": score,
                    }
                })

        def all_scores_pass(metric_value: Any) -> bool:
            """
            Recursively check if all numeric scores in the metrics meet the similarity threshold.
            """
            if isinstance(metric_value, dict):
                return all(all_scores_pass(v) for v in metric_value.values())
            elif isinstance(metric_value, (int, float)):
                return metric_value >= self.similarity_threshold
            else:
                # If the metric value is neither a dict nor a number, assume it's passing.
                return True

        pass_status = all_scores_pass(metrics)

        return {
            "metrics": metrics,
            "evaluations": detailed_comparison,
            "pass": pass_status,
        }