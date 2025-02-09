import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

#
from beanie import init_beanie
from fastapi import Depends, FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

#
from app.backend.core.config import app_configs, settings
from src.pipeline.paprocessing.run import PAProcessingPipeline

#
from .core.database import User, db
from .paprocessing.models import PAProcessingRequest
from .users.manager import auth_backend, current_active_user, fastapi_users
from .users.schemas import UserCreate, UserRead, UserUpdate

#
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#
pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncGenerator:
    # startup
    await init_beanie(db, document_models=[User], skip_indexes=True)
    yield
    # shutdown


app = FastAPI(**app_configs, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGINS_REGEX,
    allow_credentials=True,
    allow_methods=("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"),
    allow_headers=settings.CORS_HEADERS,
)


# middleware test
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


@app.get("/authenticated-route")
async def authenticated_route(user: User = Depends(current_active_user)):
    return {"message": f"Hello {user.email}!"}


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    #
    return {"status": "We are doing ok!"}


@app.post("/process_pa")
async def process_pa(request: PAProcessingRequest):
    """
    Run the Prior Authorization Processing Pipeline.

    - Accepts file paths or URLs to PDF documents.
    - Optionally takes a case ID to group them.
    - Optionally sets `use_o1` to True if you want to use the O1 model for final determination.

    Returns JSON with the pipeline results, including:
      - caseId
      - message about success/failure
      - pipeline results stored in `pa_pipeline.results[caseId]`.
    """
    start_time = time.time()

    if request.caseId:
        pa_pipeline.caseId = request.caseId

    try:
        logger.info(
            f"Starting PAProcessingPipeline.run() for caseId={pa_pipeline.caseId}"
        )

        print(request.uploaded_files)

        # Validate and sanitize input data
        sanitized_files = [
            file for file in request.uploaded_files if file.endswith(".pdf")
        ]

        await pa_pipeline.run(
            uploaded_files=sanitized_files,
            streamlit=request.streamlit,
            caseId=request.caseId if request.caseId is not None else "",
            use_o1=request.use_o1,
        )

        results_for_case = pa_pipeline.results.get(pa_pipeline.caseId, {})
        elapsed = round(time.time() - start_time, 2)

        return {
            "caseId": pa_pipeline.caseId,
            "message": f"PA processing completed in {elapsed} seconds.",
            "results": results_for_case,
        }

    except Exception as e:
        logger.error(f"Failed to process PA request: {str(e)}", exc_info=True)
        return {
            "caseId": pa_pipeline.caseId,
            "error": "An internal error has occurred. Please try again later.",
            "results": {},
        }
