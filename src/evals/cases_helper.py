import asyncio
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Union

from rapidfuzz import fuzz

from src.extractors.pdfhandler import OCRHelper
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.promptEngineering.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.storage.blob_helper import AzureBlobManager
from utils.ml_logging import get_logger


class CaseManager:
    def __init__(self, cases: Dict[str, Any]):
        """
        Initialize the CaseManager with a dictionary of cases.
        """
        self.cases = cases
        self.data_extractor = ClinicalDataExtractor()
        self.logger = get_logger()
        self.temp_dir = "tempClinicalExtractor"
        self.results = {}
        self.azure_blob_storage_account_name = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
        self.azure_blob_storage_account_key = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
        self.container_name = os.getenv("AZURE_BLOB_CONTAINER_NAME")
        self.blob_manager = AzureBlobManager(
            storage_account_name=self.azure_blob_storage_account_name,
            account_key=self.azure_blob_storage_account_key,
            container_name=self.container_name,
        )

    def cleanup_temp_dir(self) -> None:
        """
        Cleans up the temporary directory used for processing files.
        """
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            self.logger.error(
                f"Failed to clean up temporary directory '{self.temp_dir}': {e}"
            )

    def upload_files_to_blob(
        self, uploaded_files: Union[str, List[str]], step: str
    ) -> List[str]:
        """
        Upload files to Azure Blob Storage.

        Args:
            uploaded_files: List of file paths to upload.
            step: The directory name to organize these files in the blob storage.

        Returns:
            List of URLs for uploaded files.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]

        remote_files = []
        for file_path in uploaded_files:
            try:
                file_name = os.path.basename(file_path)
                destination_blob_path = f"{step}/{file_name}"
                self.blob_manager.upload_file(
                    file_path, destination_blob_path, overwrite=True
                )
                full_url = f"https://{self.azure_blob_storage_account_name}.blob.core.windows.net/{self.container_name}/{destination_blob_path}"
                remote_files.append(full_url)
                self.logger.info(f"Uploaded {file_path} to {full_url}.")
            except Exception as e:
                self.logger.error(f"Failed to upload {file_path}: {e}")

        return remote_files

    def process_uploaded_files(
        self, uploaded_files: Union[str, List[str]]
    ) -> List[str]:
        """
        Process uploaded files and extract images.

        Args:
            uploaded_files: File path or list of file paths representing the uploaded PDFs.

        Returns:
            List of extracted image file paths.
        """
        if isinstance(uploaded_files, str):
            uploaded_files = [uploaded_files]

        ocr_helper = OCRHelper(
            storage_account_name=self.azure_blob_storage_account_name,
            container_name=self.container_name,
            account_key=self.azure_blob_storage_account_key,
        )
        image_files = []
        for file_path in uploaded_files:
            try:
                output_paths = ocr_helper.extract_images_from_pdf(
                    input_path=file_path, output_path=self.temp_dir
                )
                self.logger.info(f"Extracted images: {output_paths}")
                image_files.extend(output_paths)
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {e}")

        return image_files

    def evaluate_similarity(
        self,
        extracted: Dict[str, Any],
        expected: Dict[str, Any],
        threshold: float = 95.0,
    ) -> Dict[str, Any]:
        """
        Evaluate similarity scores for each key-value pair.

        Args:
            extracted: Extracted data.
            expected: Expected data.
            threshold: Minimum similarity percentage for passing.

        Returns:
            Dictionary with similarity scores and pass status.
        """
        similarity_scores = {}
        detailed_comparison = []
        for key, expected_value in expected.items():
            if isinstance(expected_value, dict) and isinstance(
                extracted.get(key), dict
            ):
                nested_scores = self.evaluate_similarity(
                    extracted.get(key, {}), expected_value, threshold
                )
                similarity_scores[key] = nested_scores["similarity_scores"]
                detailed_comparison.extend(nested_scores["detailed_comparison"])
            else:
                extracted_value = extracted.get(key, "")
                score = fuzz.ratio(str(extracted_value), str(expected_value))
                similarity_scores[key] = score
                detailed_comparison.append(
                    {
                        "key": key,
                        "extracted_value": extracted_value,
                        "expected_value": expected_value,
                        "similarity_score": score,
                    }
                )

        pass_status = all(
            score >= threshold
            for score in similarity_scores.values()
            if isinstance(score, (int, float))
        )
        return {
            "similarity_scores": similarity_scores,
            "detailed_comparison": detailed_comparison,
            "pass": pass_status,
        }

    async def process_case(self, case_id: str, threshold: float = 95.0):
        """
        Process a single case.

        Args:
            case_id: Case ID.
            threshold: Similarity threshold for passing.
        """
        case = self.cases.get(case_id)
        if not case:
            self.logger.error(f"Case {case_id} not found.")
            return

        uploaded_files = case["uploaded_files"]
        expected_output = case["expected_output"]

        image_files = self.process_uploaded_files(uploaded_files)

        try:
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
                extracted_results["ocr_ner_results"],
                expected_output["ocr_ner_results"],
                threshold,
            )

            # Update case results
            self.results[case_id] = {
                "extracted_output": extracted_results,
                "similarity_scores": evaluation["similarity_scores"],
                "detailed_comparison": evaluation["detailed_comparison"],
                "pass": evaluation["pass"],
                "timestamp": datetime.now().isoformat(),
            }

            # Log detailed comparison
            self.logger.info(
                f"Case {case_id} detailed comparison: {evaluation['detailed_comparison']}"
            )

        except Exception as e:
            self.logger.error(f"Error processing case {case_id}: {e}")
            self.results[case_id] = {
                "extracted_output": None,
                "similarity_scores": {},
                "detailed_comparison": [],
                "pass": False,
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
            }

    async def process_all_cases(self, threshold: float = 95.0):
        """
        Process all cases.

        Args:
            threshold: Similarity threshold for passing.
        """
        tasks = [self.process_case(case_id, threshold) for case_id in self.cases.keys()]
        await asyncio.gather(*tasks)

    def get_results(self) -> Dict[str, Any]:
        """
        Retrieve results for all cases.

        Returns:
            Dictionary containing all case results.
        """
        return self.results

    def save_results_to_json(self, output_dir: str) -> None:
        """
        Save the results to JSON files in the specified output directory.

        Args:
            output_dir: The base directory to save the results.
        """
        for case_id, result in self.results.items():
            case_dir = os.path.join(
                output_dir, case_id, datetime.now().strftime("%Y%m%d_%H%M%S")
            )
            os.makedirs(case_dir, exist_ok=True)
            result_file = os.path.join(case_dir, "evaluation_results.json")
            with open(result_file, "w") as f:
                json.dump(result, f, indent=4)
            self.logger.info(f"Saved results for case {case_id} to {result_file}")
