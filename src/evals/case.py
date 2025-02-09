import json
import os
import tempfile
from contextlib import contextmanager
from typing import List, Dict, Any, Optional

class Evaluation:
    """
    Represents a single evaluation record.

    Attributes:
      - query: The expected output key (e.g. "patient_info.patient_name").
      - response: The AI-generated response.
      - context: A description of the evaluation context (for OCRNEREvaluation, this is None).
      - ground_truth: The expected value from the YAML.
      - conversation: A list of messages (for OCRNEREvaluation, this is None).
      - scores: A dictionary of score(s) (e.g. {"semantic_similarity": <score>}).
    """
    def __init__(
        self,
        query: str,
        response: str,
        ground_truth: str,
        context: Optional[Any] = None,
        conversation: Optional[Any] = None,
        scores: Optional[Dict[str, Any]] = None
    ):
        self.query = query
        self.response = response
        self.context = context
        self.ground_truth = ground_truth
        self.conversation = conversation
        self.scores = scores if scores is not None else {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "response": self.response,
            "ground_truth": self.ground_truth,
            "context": self.context,         # For OCRNEREvaluation, this will be None.
            "conversation": self.conversation, # For OCRNEREvaluation, this will be None.
            "scores": self.scores
        }

class Case:
    """
    Represents a test case.

    Attributes:
      - case_name: The case identifier.
      - case_class: A string reference to the evaluator class.
      - evaluations: A list of Evaluation objects.
      - azure_eval_result: (Optional) The result returned from the Azure evaluation API.
    """
    def __init__(self, case_name: str, case_class: str, evaluations: Optional[List[Evaluation]] = None):
        self.case_name = case_name
        self.case_class = case_class
        self.evaluations = evaluations if evaluations is not None else []
        self.azure_eval_result = None

    @contextmanager
    def create_evaluation_dataset(self):
        """
        Creates a temporary JSON Lines (jsonl) file that contains all evaluations.
        This file is later passed to the Azure AI evaluation API.
        """
        temp_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.jsonl', prefix='evaluation_dataset_')
        try:
            for eval_obj in self.evaluations:
                temp_file.write(json.dumps(eval_obj.to_dict()) + "\n")
            temp_file.flush()
            temp_file.close()
            yield temp_file.name
        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)