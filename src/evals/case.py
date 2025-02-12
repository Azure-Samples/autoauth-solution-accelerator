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
      - ground_truth: The expected value from the YAML.
      - context: A description of the evaluation context.
      - conversation: A list of messages.
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
        self.ground_truth = ground_truth

        # Only set attributes if they are not None or not an empty dict.
        if context is not None and context != {}:
            self.context = context
        if conversation is not None and conversation != {}:
            self.conversation = conversation
        if scores is not None and scores != {}:
            self.scores = scores

    def to_dict(self) -> Dict[str, Any]:
        # Build a dictionary from the instance's __dict__.
        # This will only include attributes that were actually set.
        return self.__dict__


class Case:
    """
    Represents a test case.

    Attributes:
      - case_name: The case identifier.
      - metrics: A list of evaluator/metric names.
      - config: A dictionary containing additional test case configuration (e.g., OCRNEREvaluator settings).
      - evaluations: A list of Evaluation objects.
    """

    def __init__(
        self,
        case_name: str,
        metrics: Optional[List[str]] = None,
        config: Optional[dict] = None,
        evaluations: Optional[List] = None
    ):
        self.case_name = case_name
        self.metrics = metrics if metrics is not None else []
        self.config = config if config is not None else {}
        self.evaluations = evaluations if evaluations is not None else []
        self.azure_eval_result = None

    @contextmanager
    def create_evaluation_dataset(self):
        """
        Creates a temporary JSON Lines (jsonl) file that contains all evaluations.
        This file is later passed to the Azure AI evaluation API.
        """
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix='.jsonl',
            prefix='evaluation_dataset_'
        )
        try:
            for eval_obj in self.evaluations:
                temp_file.write(json.dumps(eval_obj.to_dict()) + "\n")
            temp_file.flush()
            temp_file.close()
            yield temp_file.name
        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)