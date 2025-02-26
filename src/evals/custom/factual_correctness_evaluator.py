import asyncio
from typing import TypedDict, Dict, Any
import os
from ragas.dataset_schema import SingleTurnSample
from ragas.metrics._factual_correctness import FactualCorrectness
from langchain_community.chat_models import AzureChatOpenAI
from ragas.llms import LangchainLLMWrapper


class FactualCorrectnessScore(TypedDict):
    """
    TypedDict for the factual correctness score.
    """
    factual_correctness: float


class FactualCorrectnessEvaluator:
    """
    Evaluator class that uses RAGAS's FactualCorrectness metric with an Azure OpenAI LLM.
    """

    def __init__(
        self,
        model_config: Dict[str, Any],
    ):
        """
        Initialize the evaluator with the Azure LLM and the RAGAS metric.

        :param model_config: Dictionary containing Azure configuration values. For example:
            {
                "azure_endpoint": "https://YOUR_AZURE_RESOURCE_NAME.openai.azure.com/",
                "api_key": "YOUR_AZURE_API_KEY",
                "azure_deployment": "YOUR_DEPLOYMENT_NAME"
            }
        """
        azure_endpoint = model_config["azure_endpoint"]
        azure_api_key = model_config["api_key"]
        azure_deployment = model_config["azure_deployment"]

        azure_llm = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15"),
            azure_deployment=azure_deployment,
        )
        self.llm = LangchainLLMWrapper(azure_llm)
        self.scorer = FactualCorrectness(llm=self.llm)

    def __call__(self, *, response: str, ground_truth: str, **kwargs) -> FactualCorrectnessScore:
        """
        Evaluate the factual correctness of the given response against the reference.

        :param response: The model's answer to evaluate.
        :param reference: The ground truth / context for factual comparison.
        :return: A dictionary with the factual correctness score (0.0 to 1.0).
        """
        loop = asyncio.get_event_loop()
        try:
            score = loop.run_until_complete(self._async_score(response, ground_truth))
            return {"factual_correctness": score}
        except Exception as e:
            print(f"Error during factual correctness evaluation: {e}")
            return {"factual_correctness": 0.0}

    async def _async_score(self, response: str, reference: str) -> float:
        """
        The asynchronous method that interacts with RAGAS to compute the factual correctness score.

        :param response: The model's answer.
        :param reference: The ground truth / reference.
        :return: Numeric score indicating factual correctness.
        """
        sample = SingleTurnSample(
            response=response,
            reference=reference
        )
        return await self.scorer.single_turn_ascore(sample)