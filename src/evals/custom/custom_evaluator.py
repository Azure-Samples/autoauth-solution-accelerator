import os
from abc import ABC, abstractmethod


class CustomEvaluator(ABC):
    """
    Base class for custom evaluators.

    This class supports dynamic assignment of keyword arguments as instance attributes.
    Subclasses should override the __call__ method to provide custom evaluation logic.
    """

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
        for key, value in kwargs.items():
            setattr(self, key, value)

    @abstractmethod
    def __call__(self, **kwargs):
        """
        Callable method to evaluate inputs.

        This method should be implemented by subclasses. When an instance is called,
        it should process the provided keyword arguments and return a result as a dictionary.

        Parameters:
            **kwargs: Input data for evaluation.

        Returns:
            dict: Evaluation results.
        """
        raise NotImplementedError("Subclasses must implement the __call__ method.")

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
