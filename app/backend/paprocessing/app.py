# FastAPI wrapper for full end-to-end PA processing -> Result Rest API
import os
import logging
import time
from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from src.pipeline.paprocessing.run import PAProcessingPipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PAProcessingRequest(BaseModel):
    """
    Request body format for initiating the PA Processing Pipeline.
    """
    uploaded_files: List[str]
    use_o1: bool = False
    caseId: Optional[str] = None
    streamlit: bool = False


pa_pipeline = PAProcessingPipeline(send_cloud_logs=True)

app = FastAPI(
    title="PA Processing API",
    description=(
        "FastAPI application that provides a single endpoint to run the "
        "Prior Authorization Processing Pipeline."
    ),
    version="1.0.0",
)


@app.get("/health")
def health_check():
    """
    Health-check endpoint to verify service status.
    """
    return {"status": "ok"}


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
        logger.info(f"Starting PAProcessingPipeline.run() for caseId={pa_pipeline.caseId}")
        await pa_pipeline.run(
            uploaded_files=request.uploaded_files,
            streamlit=request.streamlit,
            caseId=request.caseId,
            use_o1=request.use_o1,
        )

        results_for_case = pa_pipeline.results.get(pa_pipeline.caseId, {})
        elapsed = round(time.time() - start_time, 2)

        return {
            "caseId": pa_pipeline.caseId,
            "message": f"PA processing completed in {elapsed} seconds.",
            "results": results_for_case
        }

    except Exception as e:
        logger.error(f"Failed to process PA request: {str(e)}", exc_info=True)
        return {
            "caseId": pa_pipeline.caseId,
            "error": str(e),
            "results": {}
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
