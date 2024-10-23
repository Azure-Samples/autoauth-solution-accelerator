from typing import Optional, Dict, Literal
from utils.ml_logging import get_logger

# Set up logger
logger = get_logger()

class ModelNotFoundError(Exception):
    """
    Custom exception for model not found errors.

    Attributes:
        model_name (str): The name of the model that was not found.
        message (str): Explanation of the error.
    """

    def __init__(self, model_name: str, message: str = "Model not found"):
        self.model_name = model_name
        self.message = f"{message}: {model_name}"
        super().__init__(self.message)

    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"

# Pricing information for models
# Note: Please check if prices have changed in the official Azure pricing page:
# https://azure.microsoft.com/en-us/pricing/details/cognitive-services/openai-service/#pricing
# These prices are from 8/4/2024

MODEL_PRICING = {
    "gpt-4o": {
        "global": {"input_cost_per_1000": 0.005, "output_cost_per_1000": 0.015},
        "regional": {"input_cost_per_1000": 0.005, "output_cost_per_1000": 0.015}
    },
    "gpt-4o-mini": {
        "global": {"input_cost_per_1000": 0.00015, "output_cost_per_1000": 0.0006},
        "regional": {"input_cost_per_1000": 0.000165, "output_cost_per_1000": 0.00066}
    },
    "gpt-3.5-turbo-0125": {
        "default": {"input_cost_per_1000": 0.0005, "output_cost_per_1000": 0.0015}
    },
    "gpt-4-turbo": {
        "default": {"input_cost_per_1000": 0.01, "output_cost_per_1000": 0.03}
    },
    "gpt-4-turbo-vision": {
        "default": {"input_cost_per_1000": 0.01, "output_cost_per_1000": 0.03}
    },
    "gpt-4": {
        "default": {"input_cost_per_1000": 0.03, "output_cost_per_1000": 0.06}
    },
    "gpt-4-32k": {
        "default": {"input_cost_per_1000": 0.06, "output_cost_per_1000": 0.12}
    }
}

def calculate_processing_cost(
        model_name: str,
        deployment_type: Optional[Literal['global', 'regional']] = 'regional',
        num_input_tokens: int = 0,
        num_output_tokens: Optional[int] = 0
    ) -> Dict[str, float]:
    """
    Calculate the processing cost for a given model and number of tokens.

    :param model_name: The name of the language model.
    :param deployment_type: The deployment type of the model (global, regional). Defaults to 'regional'.
    :param num_input_tokens: The number of input tokens.
    :param num_output_tokens: (optional) The number of output tokens. Defaults to 0.
    :return: A dictionary with the input cost, output cost, and total cost.
    :raises ModelNotFoundError: If the specified model name or deployment type is not found in the pricing information.
    """
    model_name = model_name.lower().replace(' ', '-')
    deployment_type = (deployment_type or 'regional').lower()

    if model_name not in MODEL_PRICING or deployment_type not in MODEL_PRICING[model_name]:
        logger.error(f"Model {model_name} with deployment type {deployment_type} not found in pricing information.")
        raise ModelNotFoundError(f"Model {model_name} with deployment type {deployment_type} not found in pricing information.")

    pricing_info = MODEL_PRICING[model_name][deployment_type]
    input_cost = (num_input_tokens / 1000) * pricing_info["input_cost_per_1000"]
    output_cost = (num_output_tokens / 1000) * pricing_info["output_cost_per_1000"]
    total_cost = input_cost + output_cost

    logger.info(f"Model: {model_name}, Deployment: {deployment_type}")
    logger.info(f"Input tokens: {num_input_tokens}, Output tokens: {num_output_tokens}")
    logger.info(f"Input cost: ${input_cost:.4f}, Output cost: ${output_cost:.4f}, Total cost: ${total_cost:.4f}")

    return {"input_cost": input_cost, "output_cost": output_cost, "total_cost": total_cost}

