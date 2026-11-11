"""Standalone reviewer UI server (no Azure credentials needed).

Run from the repository root::

    uvicorn app.backend.api.app:app --port 8000

When ``app/frontend/web/dist`` exists (after ``npm run build``) the built UI is
served from ``/``. During development run ``npm run dev`` in
``app/frontend/web``; Vite proxies ``/api`` to this server.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .cases import router as cases_router
from .indexes import router as indexes_router

WEB_DIST = Path(__file__).resolve().parents[2] / "frontend" / "web" / "dist"

app = FastAPI(title="AutoAuth Reviewer API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AUTOAUTH_UI_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(cases_router)
app.include_router(indexes_router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


if WEB_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = (WEB_DIST / path).resolve()
        if path and candidate.is_file() and WEB_DIST in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")
