from src.aoai.aoai_helper import AzureOpenAIManager
from typing import Optional


def create_azure_openai_manager(
    api_key: Optional[str], azure_endpoint: str, api_version: str, deployment_id: str
) -> AzureOpenAIManager:
    """
    Create a new Azure OpenAI Manager instance.

    :param api_key: API key for Azure OpenAI. Pass None to use Entra ID / managed identity.
    :param azure_endpoint: API endpoint for Azure OpenAI.
    :param api_version: API version for Azure OpenAI.
    :param deployment_id: Deployment ID for Azure OpenAI.
    :return: AzureOpenAIManager instance.
    """
    return AzureOpenAIManager(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        api_version=api_version,
        chat_model_name=deployment_id,
    )
