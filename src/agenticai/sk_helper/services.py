from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
    from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings


class Services(str, Enum):
    """Enum for supported chat completion services.

    For service specific settings, refer to this documentation:
    https://github.com/microsoft/semantic-kernel/blob/main/python/samples/concepts/setup/ALL_SETTINGS.md
    """

    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    AZURE_AI_INFERENCE = "azure_ai_inference"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    GOOGLE_AI = "google_ai"
    MISTRAL_AI = "mistral_ai"
    OLLAMA = "ollama"
    ONNX = "onnx"
    VERTEX_AI = "vertex_ai"
    
service_id = "default"

def get_chat_completion_service_and_request_settings(
    service_name: Services,
) -> tuple["ChatCompletionClientBase", "PromptExecutionSettings"]:
    """Return service and request settings."""
    chat_services = {
        Services.OPENAI: get_openai_chat_completion_service_and_request_settings,
        Services.AZURE_OPENAI: get_azure_openai_chat_completion_service_and_request_settings,
        Services.AZURE_AI_INFERENCE: get_azure_ai_inference_chat_completion_service_and_request_settings,
        # Services.ANTHROPIC: get_anthropic_chat_completion_service_and_request_settings,
        # Services.BEDROCK: get_bedrock_chat_completion_service_and_request_settings,
        # Services.GOOGLE_AI: get_google_ai_chat_completion_service_and_request_settings,
        # Services.MISTRAL_AI: get_mistral_ai_chat_completion_service_and_request_settings,
        # Services.OLLAMA: get_ollama_chat_completion_service_and_request_settings,
        # Services.ONNX: get_onnx_chat_completion_service_and_request_settings,
        # Services.VERTEX_AI: get_vertex_ai_chat_completion_service_and_request_settings,
    }
    return chat_services[service_name]()

def get_openai_chat_completion_service_and_request_settings() -> tuple[
"ChatCompletionClientBase", "PromptExecutionSettings"
]:
    """Return OpenAI chat completion service and request settings.

    The service credentials can be read by 3 ways:
    1. Via the constructor
    2. Via the environment variables
    3. Via an environment file

    The request settings control the behavior of the service. The default settings are sufficient to get started.
    However, you can adjust the settings to suit your needs.
    Note: Some of the settings are NOT meant to be set by the user.
    Please refer to the Semantic Kernel Python documentation for more information:
    https://learn.microsoft.com/en-us/python/api/semantic-kernel/semantic_kernel?view=semantic-kernel-python
    """
    from semantic_kernel.connectors.ai.open_ai import (
        OpenAIChatCompletion,
        OpenAIChatPromptExecutionSettings,
    )

    chat_service = OpenAIChatCompletion(service_id=service_id)
    request_settings = OpenAIChatPromptExecutionSettings(
        service_id=service_id, max_tokens=2000, temperature=0.7, top_p=0.8
    )

    return chat_service, request_settings


def get_azure_openai_chat_completion_service_and_request_settings() -> tuple[
    "ChatCompletionClientBase", "PromptExecutionSettings"
]:
    """Return Azure OpenAI chat completion service and request settings.

    The service credentials can be read by 3 ways:
    1. Via the constructor
    2. Via the environment variables
    3. Via an environment file

    The request settings control the behavior of the service. The default settings are sufficient to get started.
    However, you can adjust the settings to suit your needs.
    Note: Some of the settings are NOT meant to be set by the user.
    Please refer to the Semantic Kernel Python documentation for more information:
    https://learn.microsoft.com/en-us/python/api/semantic-kernel/semantic_kernel?view=semantic-kernel
    """
    from semantic_kernel.connectors.ai.open_ai import (
        AzureChatCompletion,
        AzureChatPromptExecutionSettings,
    )

    chat_service = AzureChatCompletion(service_id=service_id)
    request_settings = AzureChatPromptExecutionSettings(service_id=service_id)

    return chat_service, request_settings


def get_azure_ai_inference_chat_completion_service_and_request_settings() -> tuple[
    "ChatCompletionClientBase", "PromptExecutionSettings"
]:
    """Return Azure AI Inference chat completion service and request settings.

    The service credentials can be read by 3 ways:
    1. Via the constructor
    2. Via the environment variables
    3. Via an environment file

    The request settings control the behavior of the service. The default settings are sufficient to get started.
    However, you can adjust the settings to suit your needs.
    Note: Some of the settings are NOT meant to be set by the user.
    Please refer to the Semantic Kernel Python documentation for more information:
    https://learn.microsoft.com/en-us/python/api/semantic-kernel/semantic_kernel?view=semantic-kernel
    """
    from semantic_kernel.connectors.ai.azure_ai_inference import (
        AzureAIInferenceChatCompletion,
        AzureAIInferenceChatPromptExecutionSettings,
    )

    chat_service = AzureAIInferenceChatCompletion(
        service_id=service_id,
        ai_model_id="id",  # The model ID is simply an identifier as the model id cannot be obtained programmatically.
    )
    request_settings = AzureAIInferenceChatPromptExecutionSettings(service_id=service_id)

    return chat_service, request_settings
