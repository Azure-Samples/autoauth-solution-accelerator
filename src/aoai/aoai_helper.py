"""
`azure_openai.py` is a module for managing interactions with the Azure OpenAI API within our application.

"""

import base64
import json
import mimetypes
import os
import time
import traceback
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import openai
import requests
from azure.core.credentials import TokenCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI

from src.aoai.tokenizer import AzureOpenAITokenizer
from src.utils.ml_logging import get_logger

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = get_logger()


class AzureOpenAIManager:
    """
    A manager class for interacting with the Azure OpenAI API.

    This class provides methods for generating text completions and chat responses using the Azure OpenAI API.
    It also provides methods for validating API configurations and getting the OpenAI client.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        azure_endpoint: Optional[str] = None,
        completion_model_name: Optional[str] = None,
        chat_model_name: Optional[str] = None,
        embedding_model_name: Optional[str] = None,
        dalle_model_name: Optional[str] = None,
        whisper_model_name: Optional[str] = None,
        credential: Optional[TokenCredential] = None,
    ):
        """
        Initializes the Azure OpenAI Manager with necessary configurations.

        :param api_key: The Azure OpenAI Key. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_KEY".
        :param api_version: The Azure OpenAI API Version. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_API_VERSION" or default to "2023-05-15".
        :param azure_endpoint: The Azure OpenAI API Endpoint. If not provided, it will be fetched from the environment variable "AZURE_OPENAI_ENDPOINT".
        :param completion_model_name: The Completion Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_COMPLETION_MODEL_DEPLOYMENT_ID".
        :param chat_model_name: The Chat Model Name. If not provided, it will be fetched from the environment variable "AZURE_AOAI_CHAT_MODEL_NAME".
        :param embedding_model_name: The Embedding Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_EMBEDDING_DEPLOYMENT_ID".
        :param dalle_model_name: The DALL-E Model Deployment ID. If not provided, it will be fetched from the environment variable "AZURE_AOAI_DALLE_MODEL_DEPLOYMENT_ID".

        """
        self.api_key = api_key or os.getenv("AZURE_OPENAI_KEY")

        self.api_version = (
            api_version or os.getenv("AZURE_OPENAI_API_VERSION") or "2024-02-01"
        )
        self.azure_endpoint = azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.completion_model_name = completion_model_name or os.getenv(
            "AZURE_AOAI_COMPLETION_MODEL_DEPLOYMENT_ID"
        )
        self.chat_model_name = chat_model_name or os.getenv(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
        )
        self.embedding_model_name = embedding_model_name or os.getenv(
            "AZURE_OPENAI_EMBEDDING_DEPLOYMENT"
        )

        self.dalle_model_name = dalle_model_name or os.getenv(
            "AZURE_AOAI_DALLE_MODEL_DEPLOYMENT_ID"
        )

        self.whisper_model_name = whisper_model_name or os.getenv(
            "AZURE_AOAI_WHISPER_MODEL_DEPLOYMENT_ID"
        )

        # self.gpt5_model_name = os.getenv("AZURE_OPENAI_GPT5_DEPLOYMENT_ID")
        # self.gpt5_api_version = os.getenv("AZURE_OPENAI_GPT5_API_VERSION")
        # self.o1_model_name = os.getenv("AZURE_OPENAI_REASONING_DEPLOYMENT_ID", "o1-preview")
        self.o_reasoning_model_name = os.getenv("AZURE_OPENAI_REASONING_MODEL_ID")

        self.o_reasoning_api_version = (
            os.getenv("AZURE_OPENAI_REASONING_API_VERSION")
            or os.getenv("AZURE_OPENAI_REASONING_API_VERSION")
            or self.api_version
        )

        self.v1_base_url = self._build_v1_base_url(self.azure_endpoint)
        self._chat_use_v1 = self._env_flag_enabled(
            "AZURE_OPENAI_CHAT_DEPLOYMENT_USE_V1"
        )
        self._reasoning_use_v1 = self._env_flag_enabled(
            "AZURE_OPENAI_REASONING_DEPLOYMENT_USE_V1"
        )
        self._force_legacy_chat = self._env_flag_enabled(
            "AZURE_OPENAI_FORCE_CHAT_COMPLETIONS"
        )
        allow_fallback_flag = os.getenv("AZURE_OPENAI_ALLOW_CHAT_FALLBACK")
        self._allow_legacy_chat_fallback = (
            True
            if allow_fallback_flag is None
            else self._env_flag_enabled("AZURE_OPENAI_ALLOW_CHAT_FALLBACK")
        )
        if self._force_legacy_chat:
            self._allow_legacy_chat_fallback = True

        self._credential: Optional[TokenCredential] = credential
        self._token_provider = None
        if not self.api_key:
            self._credential = self._credential or DefaultAzureCredential()
        if self._credential is not None:
            self._token_provider = get_bearer_token_provider(
                self._credential, "https://cognitiveservices.azure.com/.default"
            )

        self.openai_client = self._create_client(self.api_version)
        self.reasoning_client = (
            self.openai_client
            if self.o_reasoning_api_version == self.api_version
            else self._create_client(self.o_reasoning_api_version)
        )

        self.tokenizer = AzureOpenAITokenizer()

        self._validate_api_configurations()

    def _build_v1_base_url(self, endpoint: Optional[str]) -> Optional[str]:
        if not endpoint:
            return None
        normalized = endpoint.rstrip("/")
        if normalized.endswith("/openai"):
            normalized = normalized[: -len("/openai")]
        if not normalized.endswith("/openai"):
            normalized = f"{normalized}/openai"
        return f"{normalized}/v1/"

    def _create_client(self, api_version: str) -> AzureOpenAI:
        client_kwargs: Dict[str, Any] = {
            "api_version": api_version,
            "azure_endpoint": self.azure_endpoint,
        }

        if self._token_provider and not self.api_key:
            client_kwargs["azure_ad_token_provider"] = self._token_provider
        else:
            client_kwargs["api_key"] = self.api_key

        return AzureOpenAI(**client_kwargs)

    def _resolve_model_for_request(self, model: Optional[str]) -> Tuple[str, bool]:
        alias = (model or "").strip().lower()

        built_in_aliases: Dict[str, Optional[str]] = {
            key: value
            for key, value in (
                ("o3-mini", self.o_reasoning_model_name),
                ("o3mini", self.o_reasoning_model_name),
                ("o1", getattr(self, "o1_model_name", None)),
                ("o1-mini", getattr(self, "o1_model_name", None)),
            )
            if value is not None
        }

        dynamic_aliases: Dict[str, Optional[str]] = {}
        alias_config = os.getenv("AZURE_OPENAI_MODEL_ALIASES")
        if alias_config:
            try:
                parsed_config = json.loads(alias_config)
                if isinstance(parsed_config, dict):
                    dynamic_aliases = {
                        str(key).strip().lower(): value
                        for key, value in parsed_config.items()
                    }
                else:
                    logger.warning(
                        "AZURE_OPENAI_MODEL_ALIASES must be a JSON object mapping aliases to deployments; ignoring."
                    )
            except (TypeError, ValueError):
                logger.warning(
                    "Failed to parse AZURE_OPENAI_MODEL_ALIASES; ignoring dynamic alias configuration."
                )

        alias_map: Dict[str, Optional[str]] = {**built_in_aliases, **dynamic_aliases}

        resolved = alias_map.get(alias, model)

        if resolved is None:
            resolved = model or self.chat_model_name

        is_reasoning = False
        if resolved:
            lowered = resolved.lower()
            is_reasoning = any(token in lowered for token in ("o1", "o3", "reasoning"))

        return resolved, is_reasoning

    def _choose_client(self, model: str, prefer_reasoning: bool = False) -> AzureOpenAI:
        if prefer_reasoning:
            return self.reasoning_client

        return self.openai_client

    @staticmethod
    def _env_flag_enabled(name: str) -> bool:
        value = os.getenv(name)
        if value is None:
            return False
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "y", "on"}

    def _get_v1_client(self) -> Optional[OpenAI]:
        if not self.v1_base_url:
            return None

        client_kwargs: Dict[str, Any] = {
            "base_url": self.v1_base_url,
        }

        if self._token_provider and not self.api_key:
            client_kwargs["api_key"] = self._token_provider()
        elif self.api_key:
            client_kwargs["api_key"] = self.api_key
        else:
            return None

        return OpenAI(**client_kwargs)

    def _use_v1_inferencing(self, model: str, *, is_reasoning: bool = False) -> bool:
        if not model:
            return False
        if self.v1_base_url is None:
            return False
        if is_reasoning:
            return self._reasoning_use_v1
        return self._chat_use_v1

    def _extract_output_text(self, response: Any) -> str:
        if response is None:
            return ""

        try:
            output_text = getattr(response, "output_text", None)
            if output_text:
                if isinstance(output_text, (list, tuple)):
                    return "".join(str(item) for item in output_text if item)
                return str(output_text)

            chunks: List[str] = []

            output_items = getattr(response, "output", None)
            if output_items:
                for item in output_items:
                    item_type = getattr(item, "type", None)
                    if item_type == "message":
                        for content in getattr(item, "content", []) or []:
                            text = getattr(content, "text", None)
                            if text:
                                chunks.append(text)
                    elif item_type == "text":
                        text = getattr(item, "text", None)
                        if text:
                            chunks.append(text)

            choices = getattr(response, "choices", None)
            if choices:
                for choice in choices:
                    message = getattr(choice, "message", None)
                    if not message:
                        continue
                    text_value = getattr(message, "content", None)
                    if isinstance(text_value, str):
                        chunks.append(text_value)
                        continue
                    for content in getattr(message, "content", []) or []:
                        text = getattr(content, "text", None)
                        if text:
                            chunks.append(text)

            return "".join(chunks)
        except Exception:  # pragma: no cover - defensive
            logger.debug("Failed to extract response text", exc_info=True)
            return ""

    def _convert_messages_to_responses_format(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Convert messages from chat completions format to Responses API format.

        Changes:
        - 'text' type → 'input_text' for user/system messages
        - 'text' type → 'output_text' for assistant messages
        - 'image_url' type → 'input_image' for images
        """
        converted_messages = []

        for message in messages:
            role = message.get("role", "")
            content = message.get("content", [])

            # Handle string content
            if isinstance(content, str):
                if role == "assistant":
                    content = [{"type": "output_text", "text": content}]
                else:
                    content = [{"type": "input_text", "text": content}]

            # Convert content types
            if isinstance(content, list):
                converted_content = []
                for item in content:
                    if not isinstance(item, dict):
                        continue

                    item_type = item.get("type", "")

                    if item_type == "text":
                        # Convert 'text' to 'input_text' or 'output_text' based on role
                        new_type = (
                            "output_text" if role == "assistant" else "input_text"
                        )
                        converted_content.append(
                            {"type": new_type, "text": item.get("text", "")}
                        )
                    elif item_type == "image_url":
                        # Convert 'image_url' to 'input_image'
                        # Extract URL string from the image_url object
                        image_url_obj = item.get("image_url", {})
                        if isinstance(image_url_obj, dict):
                            image_url_str = image_url_obj.get("url", "")
                        else:
                            image_url_str = str(image_url_obj)
                        converted_content.append(
                            {"type": "input_image", "image_url": image_url_str}
                        )
                    else:
                        # Keep other types as-is
                        converted_content.append(item)

                converted_messages.append({"role": role, "content": converted_content})
            else:
                # Fallback for unexpected formats
                converted_messages.append(message)

        return converted_messages

    def _stream_response_payload(
        self, client: Any, request_kwargs: Dict[str, Any]
    ) -> Tuple[str, Any]:
        response_content = ""
        final_response: Any = None
        stream = client.responses.stream(**request_kwargs)

        try:
            for event in stream:
                event_type = getattr(event, "type", "")
                if event_type == "response.output_text.delta":
                    delta = getattr(event, "delta", "") or ""
                    if delta:
                        print(delta, end="", flush=True)
                        response_content += str(delta)
                elif event_type == "response.message.delta":
                    delta_contents = getattr(event, "delta", []) or []
                    for part in delta_contents:
                        text = getattr(part, "text", None)
                        if text:
                            print(text, end="", flush=True)
                            response_content += text
                elif event_type == "response.completed":
                    final_response = getattr(event, "response", None)
        finally:
            if hasattr(stream, "get_final_response"):
                final_response = final_response or stream.get_final_response()
            elif hasattr(stream, "final_response"):
                final_response = final_response or stream.final_response
            stream.close()

        if not response_content:
            response_content = self._extract_output_text(final_response)

        return response_content, final_response

    def _call_legacy_chat_completions(
        self,
        client: Any,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        seed: Optional[int],
        top_p: Optional[float],
        stream: bool,
        tools: Optional[List[Dict[str, Any]]],
        tool_choice: Optional[Union[str, Dict[str, Any]]],
        response_format: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> Tuple[str, Any]:
        chat_kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "tools": tools,
            "tool_choice": tool_choice,
            **kwargs,
        }

        if response_format is not None:
            chat_kwargs["response_format"] = response_format
        if temperature is not None:
            chat_kwargs["temperature"] = temperature
        if seed is not None:
            chat_kwargs["seed"] = seed
        if top_p is not None:
            chat_kwargs["top_p"] = top_p
        if max_tokens is not None:
            chat_kwargs["max_tokens"] = max_tokens

        try:
            response = client.chat.completions.create(**chat_kwargs)
        except openai.BadRequestError as exc:
            error_text = str(exc)
            if (
                "tenant" in error_text.lower()
                and "does not match" in error_text.lower()
                and self._token_provider is not None
            ):
                logger.error(
                    "Azure OpenAI rejected the Azure AD token because the tenant does not match the resource."
                )
                logger.error(
                    "Provide AZURE_OPENAI_KEY or authenticate with a token issued for the resource tenant."
                )
                self._chat_use_v1 = False
            raise
        except Exception as exc:  # pragma: no cover - unexpected
            logger.error("Legacy chat-completions call failed: %s", exc)
            raise

        if stream:
            response_content = ""
            for event in response:
                if event.choices:
                    event_text = event.choices[0].delta
                    if event_text is None or event_text.content is None:
                        continue
                    print(event_text.content, end="", flush=True)
                    response_content += event_text.content
                    time.sleep(0.001)
        else:
            response_content = response.choices[0].message.content

        return response_content, response

    def _build_reasoning_messages(
        self,
        conversation_history: List[Dict[str, Any]],
        query: str,
        system_message_content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []

        if system_message_content:
            messages.append(
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": system_message_content,
                        }
                    ],
                }
            )

        for idx, message in enumerate(conversation_history):
            if system_message_content and idx == 0 and message.get("role") == "system":
                message_content = message.get("content")
                if message_content == system_message_content:
                    continue
                if (
                    isinstance(message_content, list)
                    and len(message_content) == 1
                    and isinstance(message_content[0], dict)
                    and message_content[0].get("type") == "text"
                    and message_content[0].get("text") == system_message_content
                ):
                    continue
            role = message.get("role", "user")
            content = message.get("content", "")
            messages.append(
                {"role": role, "content": self._normalize_reasoning_content(content)}
            )

        messages.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": query}],
            }
        )

        return messages

    def _convert_reasoning_messages_for_v1(
        self, messages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role", "user")
            content_items: List[Dict[str, Any]] = []
            for item in message.get("content", []):
                if not isinstance(item, dict):
                    content_items.append(item)
                    continue

                item_type = item.get("type")
                if item_type == "text":
                    new_type = (
                        "input_text" if role in {"system", "user"} else "output_text"
                    )
                    content_items.append(
                        {"type": new_type, "text": item.get("text", "")}
                    )
                else:
                    content_items.append(item)

            converted.append({"role": role, "content": content_items})

        return converted

    def _normalize_reasoning_content(self, content: Any) -> List[Dict[str, Any]]:
        if isinstance(content, list):
            normalized: List[Dict[str, Any]] = []
            for item in content:
                if isinstance(item, dict) and "type" in item:
                    normalized.append(item)  # assume already structured
                else:
                    normalized.append({"type": "text", "text": str(item)})
            return normalized

        if isinstance(content, str):
            return [{"type": "text", "text": content}]

        try:
            serialized = json.dumps(content)
        except Exception:
            serialized = str(content)

        return [{"type": "text", "text": serialized}]

    def _extract_reasoning_output(self, response: Any) -> str:
        try:
            if hasattr(response, "output_text") and response.output_text:
                return response.output_text

            text_chunks: List[str] = []

            outputs = getattr(response, "output", None)
            if outputs:
                for item in outputs:
                    message = getattr(item, "message", None)
                    if not message:
                        continue
                    for content in getattr(message, "content", []) or []:
                        text = getattr(content, "text", None) or getattr(
                            content, "output_text", None
                        )
                        if text:
                            text_chunks.append(text)

            choices = getattr(response, "choices", None)
            if choices:
                for choice in choices:
                    message = getattr(choice, "message", None)
                    if not message:
                        continue
                    for content in getattr(message, "content", []) or []:
                        text = getattr(content, "text", None)
                        if text:
                            text_chunks.append(text)

            return "".join(text_chunks)
        except Exception:
            logger.debug("Failed to extract reasoning output", exc_info=True)
            return ""

    async def generate_reasoning_response(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        system_message_content: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
        reasoning_effort: str = "high",
        verbosity: str = "balanced",
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        model: Optional[str] = None,
        stream: bool = False,
        seed: Optional[int] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Union[str, Dict[str, Any], None] = None,
        response_format: Union[str, Dict[str, Any], None] = None,
        **kwargs,
    ) -> Optional[Dict[str, Any]]:
        """Generate a response using Azure OpenAI reasoning models such as o1 or o3-mini."""

        if stream:
            logger.warning(
                "Streaming is not currently supported for reasoning models; defaulting to non-streaming mode."
            )

        history = list(conversation_history or [])
        if system_message_content:
            system_entry = {"role": "system", "content": system_message_content}
            if not history or history[0] != system_entry:
                history.insert(0, system_entry)

        resolved_model, _ = self._resolve_model_for_request(model)
        prefer_v1 = self._use_v1_inferencing(resolved_model, is_reasoning=True)

        messages = self._build_reasoning_messages(
            conversation_history=history,
            query=query,
            system_message_content=system_message_content,
        )

        request_kwargs: Dict[str, Any] = {
            "model": resolved_model,
        }

        if prefer_v1:
            v1_client = self._get_v1_client()
            if v1_client is None:
                logger.error(
                    "V1 client could not be created. Falling back to legacy API path."
                )
            else:
                payload: Dict[str, Any] = {
                    "model": resolved_model,
                    "input": self._convert_messages_to_responses_format(messages),
                }
                if max_output_tokens is not None:
                    payload["max_output_tokens"] = max_output_tokens
                # if temperature is not None:
                #     payload["temperature"] = temperature
                # if top_p is not None:
                #     payload["top_p"] = top_p
                if tools is not None:
                    payload["tools"] = tools
                if tool_choice is not None:
                    payload["tool_choice"] = tool_choice

                # TODO: Parameterize?
                payload["reasoning"] = {"effort": reasoning_effort}

                # if response_format is not None:
                #     payload["response_format"] = response_format
                payload.update(kwargs)

                try:
                    response = v1_client.responses.create(**payload)
                    response_text = self._extract_reasoning_output(response)
                    history.append({"role": "user", "content": query})
                    history.append({"role": "assistant", "content": response_text})
                    return {
                        "response": response_text,
                        "conversation_history": history,
                    }
                except Exception as exc:
                    logger.error(
                        "V1 reasoning call failed; falling back to legacy API."
                    )
                    logger.error(f"Error details: {exc}")
                    logger.debug(traceback.format_exc())

        client = self._choose_client(resolved_model, prefer_reasoning=True)

        # Convert messages to Responses API format
        messages_converted = self._convert_messages_to_responses_format(messages)

        request_kwargs["input"] = messages_converted
        if max_output_tokens is not None:
            request_kwargs["max_output_tokens"] = max_output_tokens
        # if temperature is not None:
        #     request_kwargs["temperature"] = temperature
        # if top_p is not None:
        #     request_kwargs["top_p"] = top_p
        # if seed is not None:
        #     request_kwargs["seed"] = seed
        if tools is not None:
            request_kwargs["tools"] = tools
        if tool_choice is not None:
            request_kwargs["tool_choice"] = tool_choice
        # if response_format is not None:
        #     request_kwargs["response_format"] = response_format

        request_kwargs["reasoning"] = {"effort": reasoning_effort}
        request_kwargs.update(kwargs)

        try:
            response = client.responses.create(**request_kwargs)
        except openai.APIConnectionError as exc:
            logger.error("API Connection Error when calling reasoning model.")
            logger.error(f"Error details: {exc}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        except Exception as exc:
            logger.error("Reasoning model call failed.")
            logger.error(f"Error details: {exc}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

        response_text = self._extract_reasoning_output(response)

        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": response_text})

        return {
            "response": response_text,
            "conversation_history": history,
        }

    def get_azure_openai_client(self):
        """
        Returns the OpenAI client.

        This method is used to get the OpenAI client that is used to interact with the OpenAI API.
        The client is initialized with the API key and endpoint when the AzureOpenAIManager object is created.

        :return: The OpenAI client.
        """
        return self.openai_client

    def _validate_api_configurations(self):
        """
        Validates if all necessary configurations are set.

        This method checks if the API key and Azure endpoint are set in the OpenAI client.
        These configurations are necessary for making requests to the OpenAI API.
        If any of these configurations are not set, the method raises a ValueError.

        :raises ValueError: If the API key or Azure endpoint is not set.
        """
        if not all(
            [
                self.openai_client.api_key,
                self.azure_endpoint,
            ]
        ):
            raise ValueError(
                "One or more OpenAI API setup variables are empty. Please review your environment variables and `SETTINGS.md`"
            )

    async def async_generate_chat_completion_response(
        self,
        conversation_history: List[Dict[str, str]],
        query: str,
        system_message_content: str = """You are an AI assistant that
          helps people find information. Please be precise, polite, and concise.""",
        temperature: float = 0.7,
        deployment_name: str = None,
        max_tokens: int = 150,
        seed: int = 42,
        top_p: float = 1.0,
        **kwargs,
    ):
        """
        Asynchronously generates a text completion using Azure OpenAI's Foundation models.
        This method utilizes the chat completion API to respond to queries based on the conversation history.

        :param conversation_history: A list of past conversation messages formatted as dictionaries.
        :param query: The user's current query or message.
        :param system_message_content: Instructions for the AI on how to behave during the completion.
        :param temperature: Controls randomness in the generation, lower values mean less random completions.
        :param max_tokens: The maximum number of tokens to generate.
        :param seed: Seed for random number generator for reproducibility.
        :param top_p: Nucleus sampling parameter controlling the size of the probability mass considered for token generation.
        :return: The generated text completion or None if an error occurs.
        """

        messages_for_api = conversation_history + [
            {"role": "system", "content": system_message_content},
            {"role": "user", "content": query},
        ]

        request_kwargs: Dict[str, Any] = {
            "model": deployment_name or self.chat_model_name,
            "input": messages_for_api,
        }
        if max_tokens is not None:
            request_kwargs["max_output_tokens"] = max_tokens
        request_kwargs.update(kwargs)

        client = self._choose_client(
            deployment_name or self.chat_model_name, prefer_reasoning=False
        )

        try:
            if temperature is not None or top_p is not None or seed is not None:
                logger.debug(
                    "Responses API ignores temperature/top_p/seed in async helper; legacy fallback will honor them if triggered."
                )
            return client.responses.create(**request_kwargs)
        except AttributeError:
            logger.debug(
                "Responses API unavailable on client; falling back to legacy chat-completions for async helper."
            )
        except (openai.BadRequestError, HTTPStatusError) as exc:
            if not self._allow_legacy_chat_fallback:
                raise
            logger.warning(
                "Responses API request failed for async helper (%s); using legacy chat-completions.",
                exc,
            )

        return client.chat.completions.create(
            model=deployment_name or self.chat_model_name,
            messages=messages_for_api,
            temperature=temperature,
            max_tokens=max_tokens,
            seed=seed,
            top_p=top_p,
            **kwargs,
        )

    def transcribe_audio_with_whisper(
        self,
        audio_file_path: str,
        language: str = "en",
        prompt: str = "Transcribe the following audio file to text.",
        response_format: Literal["json", "text", "srt", "verbose_json", "vtt"] = "text",
        temperature: float = 0.5,
        timestamp_granularities: List[Literal["word", "segment"]] = [],
        extra_headers=None,
        extra_query=None,
        extra_body=None,
        timeout: Union[float, None] = None,
    ):
        """
        Transcribes an audio file using the Whisper model and returns the transcription in the specified format.

        Args:
            audio_file_path: Path to the audio file to transcribe.
            model: ID of the model to use. Currently, only 'whisper-1' is available.
            language: The language of the input audio in ISO-639-1 format.
            prompt: Optional text to guide the model's style or continue a previous audio segment.
            response_format: Format of the transcript output ('json', 'text', 'srt', 'verbose_json', 'vtt').
            temperature: Sampling temperature between 0 and 1 for randomness in output.
            timestamp_granularities: Timestamp granularities ('word', 'segment') for 'verbose_json' format.
            extra_headers: Additional headers for the request.
            extra_query: Additional query parameters for the request.
            extra_body: Additional JSON properties for the request body.
            timeout: Request timeout in seconds.

        Returns:
            Transcription object with the audio transcription.
        """
        try:
            # Create the transcription request
            result = self.openai_client.audio.transcriptions.create(
                file=open(audio_file_path, "rb"),
                model=self.whisper_model_name,
                language=language,
                prompt=prompt,
                response_format=response_format,
                temperature=temperature,
                timestamp_granularities=timestamp_granularities,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )
            return result
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None

    async def generate_chat_response_o1(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = [],
        max_completion_tokens: int = 5000,
        stream: bool = False,
        model: str = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_01", "o1-preview"),
        **kwargs,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Generates a text response using the o1-preview or o1-mini models, considering the specific requirements and limitations of these models.

        :param query: The latest query to generate a response for.
        :param conversation_history: A list of message dictionaries representing the conversation history.
        :param max_completion_tokens: Maximum number of tokens to generate. Defaults to 5000.
        :param stream: Whether to stream the response. Defaults to False.
        :param model: The model to use for generating the response. Defaults to "o1-preview".
        :return: The generated text response as a string if response_format is "text", or a dictionary containing the response and conversation history if response_format is "json_object". Returns None if an error occurs.
        """
        start_time = time.time()
        logger.info(
            f"Function generate_chat_response_o1 started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}"
        )

        try:
            user_message = {"role": "user", "content": query}

            messages_for_api = conversation_history + [user_message]
            logger.info(
                f"Sending request to Azure OpenAI at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
            )

            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages_for_api,
                # max_completion_tokens=max_completion_tokens,
                stream=stream,
                **kwargs,
            )

            if stream:
                response_content = ""
                for event in response:
                    if event.choices:
                        event_text = event.choices[0].delta
                        if event_text is None or event_text.content is None:
                            continue
                        print(event_text.content, end="", flush=True)
                        response_content += event_text.content
                        time.sleep(0.001)  # Maintain minimal sleep to reduce latency
            else:
                response_content = response.choices[0].message.content
                logger.info(f"Model_used: {response.model}")

            conversation_history.append(user_message)
            conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                f"Function generate_chat_response_o1 finished at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))} (Duration: {duration:.2f} seconds)"
            )

            return {
                "response": response_content,
                "conversation_history": conversation_history,
            }

        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            error_message = str(e)
            if "maximum context length" in error_message:
                logger.warning(
                    "Context length exceeded, reducing conversation history and retrying."
                )
                logger.warning(f"Error details: {e}")
                return "maximum context length"
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def generate_chat_response(
        self,
        query: str,
        conversation_history: List[Dict[str, str]] = [],
        image_paths: List[str] = None,
        image_bytes: List[bytes] = None,
        system_message_content: str = "You are an AI assistant that helps people find information. Please be precise, polite, and concise.",
        temperature: float = 0.7,
        max_tokens: int = 150,
        seed: int = 42,
        top_p: float = 1.0,
        stream: bool = False,
        tools: List[Dict[str, Any]] = None,
        tool_choice: Union[str, Dict[str, Any]] = None,
        response_format: Union[str, Dict[str, Any]] = "text",
        is_reasoning: bool = False,
        model: Optional[str] = None,
        **kwargs,
    ) -> Optional[Union[str, Dict[str, Any]]]:
        """
        Generates a text response considering the conversation history.

        :param query: The latest query to generate a response for.
        :param conversation_history: A list of message dictionaries representing the conversation history.
        :param image_paths: A list of paths to images to include in the query.
        :param image_bytes: A list of bytes of images to include in the query.
        :param system_message_content: The content of the system message. Defaults to a generic assistant message.
        :param temperature: Controls randomness in the output. Defaults to 0.7.
        :param max_tokens: Maximum number of tokens to generate. Defaults to 150.
        :param seed: Random seed for deterministic output. Defaults to 42.
        :param top_p: The cumulative probability cutoff for token selection. Defaults to 1.0.
        :param stream: Whether to stream the response. Defaults to False.
        :param tools: A list of tools the model can use.
        :param tool_choice: Controls which (if any) tool is called by the model. Can be "none", "auto", "required", or specify a particular tool.
        :param response_format: Specifies the format of the response. Can be:
            - A string: "text" or "json_object".
            - A dictionary specifying a custom response format, including a JSON schema when needed.
        :return: The generated text response as a string if response_format is "text", or a dictionary containing the response and conversation history if response_format is "json_object". Returns None if an error occurs.
        """
        start_time = time.time()
        logger.info(
            f"Function generate_chat_response started at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}"
        )

        try:
            resolved_model, resolved_model_is_reasoning = self._resolve_model_for_request(
                model
            )
            # Normalize reasoning flag early to avoid NameError in error paths
            is_reasoning_flag = bool(is_reasoning or resolved_model_is_reasoning)

            if tools is not None and tool_choice is None:
                logger.debug(
                    "Tools are provided but tool_choice is None. Setting tool_choice to 'auto'."
                )
                tool_choice = "auto"
            else:
                logger.debug(f"Tools: {tools}, Tool Choice: {tool_choice}")

            system_message = {"role": "system", "content": system_message_content}
            if not conversation_history or conversation_history[0] != system_message:
                conversation_history.insert(0, system_message)

            user_message = {
                "role": "user",
                "content": [{"type": "text", "text": query}],
            }

            if image_bytes:
                for image in image_bytes:
                    encoded_image = base64.b64encode(image).decode("utf-8")
                    user_message["content"].append(
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}",
                            },
                        }
                    )
            elif image_paths:
                if isinstance(image_paths, str):
                    image_paths = [image_paths]
                for image_path in image_paths:
                    try:
                        with open(image_path, "rb") as image_file:
                            encoded_image = base64.b64encode(image_file.read()).decode(
                                "utf-8"
                            )
                            mime_type, _ = mimetypes.guess_type(image_path)
                            logger.info(f"Image {image_path} type: {mime_type}")
                            mime_type = mime_type or "application/octet-stream"
                            user_message["content"].append(
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{encoded_image}",
                                    },
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error processing image {image_path}: {e}")

            messages_for_api = conversation_history + [user_message]
            logger.info(
                f"Sending request to Azure OpenAI at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
            )

            if isinstance(response_format, str):
                response_format_param = {"type": response_format}
            elif isinstance(response_format, dict):
                if response_format.get("type") == "json_schema":
                    json_schema = response_format.get("json_schema", {})
                    if json_schema.get("strict", False):
                        if "name" not in json_schema or "schema" not in json_schema:
                            raise ValueError(
                                "When 'strict' is True, 'name' and 'schema' must be provided in 'json_schema'."
                            )
                response_format_param = response_format
            else:
                raise ValueError(
                    "Invalid response_format. Must be a string or a dictionary."
                )

            if is_reasoning_flag:
                return await self.generate_reasoning_response(
                    query=query,
                    conversation_history=conversation_history,
                    system_message_content=system_message_content,
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    model=resolved_model,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice,
                    response_format=response_format,
                    seed=seed,
                    **kwargs,
                )

            prefer_v1 = self._use_v1_inferencing(resolved_model, is_reasoning=False)

            response_client: Any = None
            if prefer_v1:
                v1_client = self._get_v1_client()
                if v1_client is None:
                    logger.warning(
                        "V1 client could not be created; falling back to the primary Azure OpenAI client."
                    )
                else:
                    response_client = v1_client
            if response_client is None:
                response_client = self._choose_client(
                    resolved_model, prefer_reasoning=False
                )

            # Convert messages to Responses API format
            messages_for_responses = self._convert_messages_to_responses_format(
                messages_for_api
            )

            request_kwargs: Dict[str, Any] = {
                "model": resolved_model,
                "input": messages_for_responses,
            }
            if max_tokens is not None:
                request_kwargs["max_output_tokens"] = max_tokens
            if tools is not None:
                request_kwargs["tools"] = tools
            if tool_choice is not None:
                request_kwargs["tool_choice"] = tool_choice

            # Filter out unsupported parameters from kwargs before passing to Responses API
            unsupported_for_responses = {
                "response_format",
                "temperature",
                "top_p",
                "seed",
                "frequency_penalty",
                "presence_penalty",
            }
            filtered_kwargs = {
                k: v for k, v in kwargs.items() if k not in unsupported_for_responses
            }
            request_kwargs.update(filtered_kwargs)

            if (
                temperature is not None or top_p is not None or seed is not None
            ) and not self._force_legacy_chat:
                logger.debug(
                    "Responses API ignores temperature/top_p/seed; these will only be honored if legacy chat fallback runs."
                )
            if kwargs and any(k in unsupported_for_responses for k in kwargs):
                filtered_out = [k for k in kwargs if k in unsupported_for_responses]
                logger.debug(
                    f"Filtered unsupported parameters for Responses API: {filtered_out}"
                )

            response: Any = None
            response_content = ""
            use_legacy_chat = self._force_legacy_chat

            if not use_legacy_chat:
                try:
                    if stream:
                        response_content, response = self._stream_response_payload(
                            response_client, request_kwargs
                        )
                    else:
                        response = response_client.responses.create(**request_kwargs)
                        response_content = self._extract_output_text(response)
                except AttributeError:
                    logger.debug(
                        "Responses API unavailable on client; falling back to legacy chat-completions."
                    )
                    use_legacy_chat = True
                except (openai.BadRequestError, HTTPStatusError) as exc:
                    error_text = str(exc)
                    if (
                        "tenant" in error_text.lower()
                        and "does not match" in error_text.lower()
                        and self._token_provider is not None
                    ):
                        logger.warning(
                            "Azure OpenAI Responses API rejected the bearer token due to tenant mismatch; disabling v1 inferencing."
                        )
                        self._chat_use_v1 = False
                    if not self._allow_legacy_chat_fallback:
                        raise
                    logger.warning(
                        "Responses API request failed (%s); falling back to legacy chat-completions.",
                        exc,
                    )
                    use_legacy_chat = True
                except Exception as exc:  # pragma: no cover - defensive
                    if not self._allow_legacy_chat_fallback:
                        raise
                    logger.warning(
                        "Unexpected Responses API failure (%s); using legacy chat-completions.",
                        exc,
                    )
                    use_legacy_chat = True

            if use_legacy_chat:
                legacy_client = response_client
                if legacy_client is None or not hasattr(legacy_client, "chat"):
                    legacy_client = self._choose_client(
                        resolved_model, prefer_reasoning=False
                    )
                response_content, response = self._call_legacy_chat_completions(
                    legacy_client,
                    model=resolved_model,
                    messages=messages_for_api,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    seed=seed,
                    top_p=top_p,
                    stream=stream,
                    tools=tools,
                    tool_choice=tool_choice,
                    response_format=response_format_param,
                    **kwargs,
                )

            if not response_content and response is not None:
                response_content = self._extract_output_text(response)

            conversation_history.append(user_message)
            conversation_history.append(
                {"role": "assistant", "content": response_content}
            )

            end_time = time.time()
            duration = end_time - start_time
            logger.info(
                f"Function generate_chat_response finished at {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))} (Duration: {duration:.2f} seconds)"
            )

            # Determine if response should be parsed as JSON
            should_parse_json = False
            if isinstance(response_format, str) and response_format == "json_object":
                should_parse_json = True
            elif isinstance(response_format, dict):
                format_type = response_format.get("type", "")
                if format_type in ("json_object", "json_schema"):
                    should_parse_json = True

            if should_parse_json:
                try:
                    # Strip markdown code fences if present
                    cleaned_content = response_content.strip()
                    if cleaned_content.startswith("```"):
                        # Remove opening fence
                        lines = cleaned_content.split("\n")
                        if lines[0].startswith("```"):
                            lines = lines[1:]
                        # Remove closing fence
                        if lines and lines[-1].strip() == "```":
                            lines = lines[:-1]
                        cleaned_content = "\n".join(lines).strip()

                    parsed_response = json.loads(cleaned_content)
                    return {
                        "response": parsed_response,
                        "conversation_history": conversation_history,
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse assistant's response as JSON: {e}")
                    logger.error(f"Response content: {response_content[:500]}")
                    return {
                        "response": response_content,
                        "conversation_history": conversation_history,
                    }
            else:
                return {
                    "response": response_content,
                    "conversation_history": conversation_history,
                }

        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        except Exception as e:
            error_message = str(e)
            if "maximum context length" in error_message:
                logger.warning(
                    "Context length exceeded, reducing conversation history and retrying."
                )
                logger.warning(f"Error details: {e}")
                return "maximum context length"
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        n: Optional[int] = 1,
        quality: Optional[str] = None,
        response_format: Optional[str] = None,
        size: Optional[str] = None,
        style: Optional[str] = None,
        user: Optional[str] = None,
        extra_headers: Optional[dict] = None,
        extra_query: Optional[dict] = None,
        extra_body: Optional[dict] = None,
        timeout: Optional[float] = None,
        show_picture: Optional[bool] = False,
    ) -> Optional[str]:
        """
        Generates an image for the given prompt using Azure OpenAI's DALL-E model.

        :param prompt: A text description of the desired image(s).
        :param model: The model to use for image generation.
        :param n: The number of images to generate.
        :param quality: The quality of the image that will be generated. 'hd' creates images with finer details and greater consistency across the image.
            This param is only supported for 'dall-e-3'.
        :param response_format: The format in which the generated images are returned.
            Must be one of 'url' or 'b64_json'.
        :param size: The size of the generated images. Must be one of '256x256', '512x512', or '1024x1024' for 'dall-e-2'.
            Must be one of '1024x1024', '1792x1024', or '1024x1792' for 'dall-e-3' models.
        :param style: The style of the generated images. Must be one of 'vivid' or 'natural'.
            'Vivid' causes the model to lean towards generating hyper-real and dramatic images.
            'Natural' causes the model to produce more natural, less hyper-real looking images. This param is only supported for 'dall-e-3'.
        :param user: A unique identifier representing your end-user.
        :param extra_headers: Send extra headers.
        :param extra_query: Add additional query parameters to the request.
        :param extra_body: Add additional JSON properties to the request.
        :param timeout: Override the client-level default timeout for this request, in seconds.
        :return: The URL of the generated image, or None if an error occurred.
        :raises Exception: If an error occurs while making the API request.
        """
        try:
            response = self.openai_client.images.generate(
                prompt=prompt,
                model=model or self.dalle_model_name,
                n=n,
                quality=quality,
                response_format=response_format,
                size=size,
                style=style,
                user=user,
                extra_headers=extra_headers,
                extra_query=extra_query,
                extra_body=extra_body,
                timeout=timeout,
            )
            image_url = json.loads(response.model_dump_json())["data"][0]["url"]
            logger.info(f"Generated image URL: {image_url}")

            if show_picture:
                response_image = requests.get(image_url)
                img = mpimg.imread(BytesIO(response_image.content))

                # Create a new figure and add the image to it
                fig = plt.figure(frameon=False)
                ax = plt.Axes(fig, [0.0, 0.0, 1.0, 1.0])
                ax.set_axis_off()
                fig.add_axes(ax)

                # Display the image
                ax.imshow(img, aspect="auto")
                plt.show()

            return image_url
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None

    def generate_embedding(
        self, input_text: str, model_name: Optional[str] = None, **kwargs
    ) -> Optional[str]:
        """
        Generates an embedding for the given input text using Azure OpenAI's Foundation models.

        :param input_text: The text to generate an embedding for.
        :param model_name: The name of the model to use for generating the embedding. If None, the default embedding model is used.
        :param kwargs: Additional parameters for the API request.
        :return: The embedding as a JSON string, or None if an error occurred.
        :raises Exception: If an error occurs while making the API request.
        """
        try:
            response = self.openai_client.embeddings.create(
                input=input_text,
                model=model_name or self.embedding_model_name,
                **kwargs,
            )

            embedding = response.model_dump_json(indent=2)
            logger.info(f"Created embedding: {embedding}")
            return embedding
        except openai.APIConnectionError as e:
            logger.error("API Connection Error: The server could not be reached.")
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
        except Exception as e:
            logger.error(
                "Unexpected Error: An unexpected error occurred during contextual response generation."
            )
            logger.error(f"Error details: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None, None
