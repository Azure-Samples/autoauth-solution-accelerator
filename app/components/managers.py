from typing import Optional

from azure.core.credentials import AzureKeyCredential

from src.aoai.aoai_helper import AzureOpenAIManager


def create_azure_openai_manager(
    api_key: str, azure_endpoint: str, api_version: str, deployment_id: str
) -> AzureOpenAIManager:
    """
    Create a new Azure OpenAI Manager instance.

    :param api_key: API key for Azure OpenAI.
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
