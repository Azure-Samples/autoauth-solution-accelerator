"""
Backend proxy routes for the Policy Indexer Function App.

These endpoints forward requests from the Streamlit frontend to the
Azure Function App so the UI never needs to know the function key or URL.
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.utils.function_keys import get_indexer_function_headers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/indexer", tags=["indexer"])

_INDEXER_BASE_URL = os.getenv("INDEXER_FUNCTION_BASE_URL", "http://localhost:7071")

_TIMEOUT = httpx.Timeout(timeout=300.0)  # indexing can be slow


def _headers() -> dict[str, str]:
    return get_indexer_function_headers()


# ---------- request models ----------

class ReindexAllRequest(BaseModel):
    prefix: str = "policies_ocr/"


class ProcessBlobRequest(BaseModel):
    blob_name: str


class SetupIndexRequest(BaseModel):
    pass


# ---------- routes ----------

@router.get("/health")
async def indexer_health():
    """Proxy the indexer health-check endpoint."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{_INDEXER_BASE_URL}/api/health",
                headers=_headers(),
            )
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the indexer function app: {exc}",
            ) from exc


@router.post("/reindex_all")
async def reindex_all(body: ReindexAllRequest | None = None):
    """Trigger a full reindex of all policy PDFs."""
    payload = body.model_dump() if body else {}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{_INDEXER_BASE_URL}/api/reindex_all",
                headers=_headers(),
                json=payload,
            )
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the indexer function app: {exc}",
            ) from exc


@router.post("/setup_index")
async def setup_index():
    """Create or update the AI Search index schema."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{_INDEXER_BASE_URL}/api/setup_index",
                headers=_headers(),
            )
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the indexer function app: {exc}",
            ) from exc


@router.post("/process_blob")
async def process_blob(body: ProcessBlobRequest):
    """Manually process a specific blob."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{_INDEXER_BASE_URL}/api/process_blob_manual",
                headers=_headers(),
                json=body.model_dump(),
            )
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the indexer function app: {exc}",
            ) from exc


@router.get("/processing_status")
async def processing_status(
    session_id: str | None = None,
    blob_name: str | None = None,
    filter: str = "recent",
    limit: int = 50,
):
    """Get processing status and session history."""
    params: dict[str, str] = {"filter": filter, "limit": str(limit)}
    if session_id:
        params["session_id"] = session_id
    if blob_name:
        params["blob_name"] = blob_name

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            resp = await client.get(
                f"{_INDEXER_BASE_URL}/api/processing_status",
                headers=_headers(),
                params=params,
            )
            return resp.json()
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach the indexer function app: {exc}",
            ) from exc
