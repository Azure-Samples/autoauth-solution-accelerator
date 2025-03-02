import asyncio
import os
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Union

from rapidfuzz import fuzz

from src.evals.custom.custom_evaluator import CustomEvaluator
from src.extractors.pdfhandler import OCRHelper
from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor
from src.pipeline.promptEngineering.models import (
    ClinicalInformation,
    PatientInformation,
    PhysicianInformation,
)
from src.utils.ml_logging import get_logger


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

    def __call__(
        self, *, response: str, ground_truth: str, **kwargs
    ) -> IndelSimilarity:
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
