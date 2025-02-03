import json
import os
import subprocess

import pytest
import requests
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv

# Replace these with your actual API endpoint and Azure AD token
API_ENDPOINT = "https://apim-pauth-dev-southcentralus.azure-api.net/app"  # TODO: replace with AZD-sourced endpoint value
load_dotenv(
    "/Users/jinle/Repos/CustomerPoCs/gbb-ai-hls-factory-prior-auth/tests/apim/test.env"
)

AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
if not AZURE_CLIENT_ID:
    raise ValueError("AZURE_CLIENT_ID is not set in the environment variables")

AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
if not AZURE_CLIENT_SECRET:
    raise ValueError("AZURE_CLIENT_SECRET is not set in the environment variables")

TENANT_ID = os.getenv("TENANT_ID")
if not TENANT_ID:
    raise ValueError("TENANT_ID is not set in the environment variables")


def get_azure_ad_token():
    credential = ClientSecretCredential(
        tenant_id=TENANT_ID,
        client_id=AZURE_CLIENT_ID,
        client_secret=AZURE_CLIENT_SECRET,
    )
    token = credential.get_token("https://management.azure.com/.default")
    print(token)
    return token.token


AZURE_AD_TOKEN = get_azure_ad_token()

APIM_SUBSCRIPTION_KEY = os.getenv("APIM_SUBSCRIPTION_KEY")
if not APIM_SUBSCRIPTION_KEY:
    raise ValueError("APIM_SUBSCRIPTION_KEY is not set in the environment variables")


@pytest.fixture
def headers():
    return {
        "Authorization": f"Bearer {AZURE_AD_TOKEN}",
        "Content-Type": "application/json",
        "Ocp-Apim-Trace": "true",
        "Ocp-Apim-Subscription-Key": APIM_SUBSCRIPTION_KEY,
    }


def test_azure_ad_validation(headers):
    response = requests.get(API_ENDPOINT, headers=headers)
    assert response.status_code == 200, "Azure AD validation failed"
    assert "expected_key" in response.json(), "Response does not contain expected data"
