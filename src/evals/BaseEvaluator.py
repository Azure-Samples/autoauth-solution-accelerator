import os
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseEvaluator(ABC):
    def __init__(self, args: Dict[str, Any], threshold: float = 95.0):
        """
        Base evaluator initializer.

        Args:
            args: A dictionary of arguments for the evaluator.
            threshold: Similarity threshold for evaluations.
        """
        self.args = args
        self.threshold = threshold

    @staticmethod
    def get_required_env_var(var_name: str) -> str:
        """
        Retrieve a required environment variable and raise an error if missing.

        Args:
            var_name: The name of the environment variable.

        Returns:
            The value of the environment variable.

        Raises:
            ValueError: If the environment variable is not set.
        """
        value = os.getenv(var_name)
        if not value:
            raise ValueError(f"Missing required environment variable: {var_name}")
        return value

    @abstractmethod
    async def run(self) -> Dict[str, Any]:
        """
        Execute the evaluation.

        This method must be implemented by any subclass.

        Returns:
            A dictionary with evaluation results.
        """
        pass