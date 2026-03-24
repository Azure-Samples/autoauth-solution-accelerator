import logging
import os
from functools import lru_cache

import httpx
from azure.identity import ManagedIdentityCredential

logger = logging.getLogger(__name__)

_ARM_SCOPE = "https://management.azure.com/.default"
_LIST_KEYS_API_VERSION = "2024-04-01"


def _get_configured_function_key() -> str:
    return os.getenv("INDEXER_FUNCTION_KEY", "").strip()


def _get_function_app_resource_id() -> str:
    return os.getenv("INDEXER_FUNCTION_APP_RESOURCE_ID", "").strip()


def _get_managed_identity_credential() -> ManagedIdentityCredential:
    client_id = os.getenv("AZURE_CLIENT_ID", "").strip() or None
    return ManagedIdentityCredential(client_id=client_id)


@lru_cache(maxsize=1)
def get_indexer_function_key() -> str:
    configured_key = _get_configured_function_key()
    if configured_key:
        return configured_key

    function_app_resource_id = _get_function_app_resource_id()
    if not function_app_resource_id:
        logger.warning(
            "INDEXER_FUNCTION_KEY is not configured and INDEXER_FUNCTION_APP_RESOURCE_ID is unavailable."
        )
        return ""

    try:
        credential = _get_managed_identity_credential()
        token = credential.get_token(_ARM_SCOPE).token
        response = httpx.post(
            f"https://management.azure.com{function_app_resource_id}/host/default/listkeys",
            params={"api-version": _LIST_KEYS_API_VERSION},
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()

        function_keys = payload.get("functionKeys") or {}
        key = (function_keys.get("default") or payload.get("masterKey") or "").strip()
        if not key:
            logger.warning("Function host keys response did not include a usable key.")
        return key
    except Exception as exc:
        logger.warning("Failed to resolve Function host key via managed identity: %s", exc)
        return ""


def get_indexer_function_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    function_key = get_indexer_function_key()
    if function_key:
        headers["x-functions-key"] = function_key
    return headers