from typing import Any, Dict, TypedDict

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


class SimilarityScore(TypedDict):
    semantic_similarity: float


class SemanticSimilarityEvaluator:
    def __init__(self, model_name: str = 'bert-base-uncased'):
        """
        Initialize the evaluator with a pre-trained model for embeddings.

        :param model_name: Name of the pre-trained model from Hugging Face Transformers.
        """
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def __call__(self, *, response: str, ground_truth: str, **kwargs) -> SimilarityScore:
        """
        Calculate the semantic similarity between the response and ground truth.

        :param response: The response to evaluate.
        :param ground_truth: The ground truth to compare against.
        :return: A dictionary containing the semantic similarity score.
        """
        try:
            response_embedding = self._get_embedding(response)
            ground_truth_embedding = self._get_embedding(ground_truth)
            similarity = self._calculate_cosine_similarity(response_embedding, ground_truth_embedding)
            return {"semantic_similarity": similarity}
        except Exception as e:
            print(f"Error during evaluation: {e}")
            return {"semantic_similarity": 0.0}

    def _get_embedding(self, text: str) -> torch.Tensor:
        """
        Get the embedding for a given text.

        :param text: The input text.
        :return: The embedding as a torch tensor.
        """
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True)
        outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1)

    def _calculate_cosine_similarity(self, tensor1: torch.Tensor, tensor2: torch.Tensor) -> float:
        """
        Calculate the cosine similarity between two tensors.

        :param tensor1: First tensor.
        :param tensor2: Second tensor.
        :return: The cosine similarity score.
        """
        return F.cosine_similarity(tensor1, tensor2).item()