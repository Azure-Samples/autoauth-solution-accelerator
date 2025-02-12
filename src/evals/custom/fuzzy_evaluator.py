import os
import shutil
from datetime import datetime
from typing import Any, List, Union
import asyncio
from rapidfuzz import fuzz
from dataclasses import dataclass

from src.extractors.pdfhandler import OCRHelper
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.promptEngineering.models import ClinicalInformation, PatientInformation, PhysicianInformation
from src.utils.ml_logging import get_logger
from src.evals.custom.custom_evaluator import CustomEvaluator

# Define a dataclass for returning semantic similarity
@dataclass
class IndelSimilarity:
    indel_similarity: float

class FuzzyEvaluator(CustomEvaluator):
    def __init__(self, **kwargs):
        """
                Initialize the evaluator with any number of keyword arguments.

        All keyword arguments provided during initialization are set as attributes of the instance.

        Example:
            evaluator = CustomEvaluator(param1="value1", param2=42)
            print(evaluator.param1)  # Output: "value1"
            print(evaluator.param2)  # Output: 42

        Parameters:
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(**kwargs)
        self.logger = get_logger()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __call__(self, *, response: str, ground_truth: str, **kwargs) -> IndelSimilarity:
        """
        Computes semantic similarity between response and ground_truth.

        Signature:
            __call__(*, response: str, ground_truth: str, **kwargs) -> SemanticSimilarity

        Returns:
            A IndelSimilarity instance containing the computed semantic similarity.
        """
        try:
            similarity_score = fuzz.ratio(response, ground_truth)
        except Exception as e:
            self.logger.error(f"Error computing similarity: {e}")
            similarity_score = 0
        return IndelSimilarity(indel_similarity=similarity_score)
    #
    # async def generate_ner_responses(self) -> dict:
    #     """
    #     Generates NER responses by processing the uploaded files.
    #
    #     Returns:
    #         A dictionary with key 'generated_output' containing the extracted results.
    #     """
    #     dt_started = datetime.now().isoformat()
    #     image_files = self.process_uploaded_files(self.uploaded_files)
    #     try:
    #         result = await self.data_extractor.run(
    #             image_files=image_files,
    #             PatientInformation=PatientInformation,
    #             PhysicianInformation=PhysicianInformation,
    #             ClinicalInformation=ClinicalInformation,
    #         )
    #         extracted_results = {
    #             "ocr_ner_results": {
    #                 "patient_info": result["patient_data"].model_dump(mode="json"),
    #                 "physician_info": result["physician_data"].model_dump(mode="json"),
    #                 "clinical_info": result["clinician_data"].model_dump(mode="json"),
    #             }
    #         }
    #         final_result = {
    #             "generated_output": extracted_results["ocr_ner_results"],
    #             "dt_started": dt_started,
    #             "dt_completed": datetime.now().isoformat()
    #         }
    #         self.logger.info(f"NER response generation completed: {final_result}")
    #         return final_result
    #     except Exception as e:
    #         self.logger.error(f"Error generating NER responses: {e}")
    #         return {
    #             "generated_output": {},
    #             "dt_started": dt_started,
    #             "dt_completed": datetime.now().isoformat(),
    #             "error": str(e)
    #         }
    #     finally:
    #         self.cleanup_temp_dir()
    #
    # def cleanup_temp_dir(self) -> None:
    #     try:
    #         if os.path.exists(self.temp_dir):
    #             shutil.rmtree(self.temp_dir)
    #             self.logger.info(f"Cleaned up temporary directory: {self.temp_dir}")
    #     except Exception as e:
    #         self.logger.error(f"Failed to clean up temporary directory '{self.temp_dir}': {e}")
    #
    # def process_uploaded_files(self, uploaded_files: Union[str, List[str]]) -> List[str]:
    #     if isinstance(uploaded_files, str):
    #         uploaded_files = [uploaded_files]
    #     ocr_helper = OCRHelper()
    #     image_files = []
    #     for file_path in uploaded_files:
    #         try:
    #             output_paths = ocr_helper.extract_images_from_pdf(
    #                 input_path=file_path,
    #                 output_path=self.temp_dir
    #             )
    #             self.logger.info(f"Extracted images from {file_path}: {output_paths}")
    #             image_files.extend(output_paths)
    #         except Exception as e:
    #             self.logger.error(f"Failed to process {file_path}: {e}")
    #     return image_files

    # def __getstate__(self):
    #     """
    #     Exclude unpickleable objects (such as logger and data_extractor) from the state.
    #     """
    #     state = self.__dict__.copy()
    #     state.pop("logger", None)
    #     state.pop("data_extractor", None)
    #     return state
    #
    # def __setstate__(self, state):
    #     """
    #     Reinitialize unpickleable objects after unpickling.
    #     """
    #     self.__dict__.update(state)
    #     from src.utils.ml_logging import get_logger
    #     self.logger = get_logger()
    #     from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
    #     self.data_extractor = ClinicalDataExtractor()