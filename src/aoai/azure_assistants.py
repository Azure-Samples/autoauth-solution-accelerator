"""
azure_assistants.py is a module that defines the AzureOpenAssistantManager class for managing interactions with the Azure OpenAI API within our application. 
"""
import json
import openai
import os
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from openai import AzureOpenAI

from src.aoai.azure_openai import AzureOpenAIManager
from utils.ml_logging import get_logger

# Load environment variables from .env file
load_dotenv()

# Set up logger
logger = get_logger()


class AzureOpenAssistantManager(AzureOpenAIManager):
    def __init__(self,
                api_key: Optional[str] = None,
                api_version: Optional[str] = None,
                azure_endpoint: Optional[str] = None,
                completion_model_name: Optional[str] = None,
                chat_model_name: Optional[str] = None,
                embedding_model_name: Optional[str] = None):
        super().__init__(api_key,
                         api_version,
                         azure_endpoint,
                         completion_model_name,
                         chat_model_name,
                         embedding_model_name)
        