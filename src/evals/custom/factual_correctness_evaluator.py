import os
from typing import TypedDict

from langchain_community.chat_models import AzureChatOpenAI
from ragas.dataset_schema import SingleTurnSample
from ragas.llms import LangchainLLMWrapper
from ragas.metrics._factual_correctness import FactualCorrectness


class FactualCorrectnessScore(TypedDict):
    """
    TypedDict for the factual correctness score.
    """

    factual_correctness: float


class FactualCorrectnessEvaluator:
    """
    Evaluator that lazily initializes the Azure LLM and RAGAS scorer
    only when needed, preventing pickling issues.
    """

    def __init__(self, model_config: dict):
        """
        :param model_config: Dictionary containing Azure configuration, e.g.:
             {
                "azure_endpoint": "https://YOUR_RESOURCE_NAME.openai.azure.com/",
                "api_key": "YOUR_API_KEY",
                "azure_deployment": "YOUR_DEPLOYMENT_NAME"
             }
        """
        # Store config but do not create any unpicklable objects yet
        self.model_config = model_config

    def __call__(self, *, response: str, ground_truth: str) -> FactualCorrectnessScore:
        """
        Synchronously evaluate factual correctness.
        """
        try:
            score = self._sync_score(response, ground_truth)
            return {"factual_correctness": score}
        except Exception as e:
            print(f"Error during factual correctness evaluation: {e}")
            return {"factual_correctness": 0.0}

    def _sync_score(self, response: str, reference: str) -> float:
        """
        Helper function that builds the LLM and RAGAS scorer *on demand*.
        """
        # 1) Create the Azure LLM with config
        azure_llm = AzureChatOpenAI(
            azure_endpoint=self.model_config["azure_endpoint"],
            api_key=self.model_config["api_key"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_deployment=self.model_config["azure_deployment"],
        )
        wrapped_llm = LangchainLLMWrapper(azure_llm)

        # 2) Create a new scorer each time. It has no memory; it just runs the prompt
        scorer = FactualCorrectness(llm=wrapped_llm)

        # 3) Evaluate
        sample = SingleTurnSample(response=response, reference=reference)
        return scorer.single_turn_score(sample)
