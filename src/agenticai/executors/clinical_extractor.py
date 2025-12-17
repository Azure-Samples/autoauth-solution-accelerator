# Copyright (c) Microsoft. All rights reserved.
"""Clinical Data Extractor Executor.

This executor wraps the clinical data extraction functionality,
converting raw text input into structured patient, physician, and clinical data.
"""

import logging
from typing import Any

from agent_framework import Executor, WorkflowContext, handler

from src.agenticai.messages import PAProcessingRequest, ExtractionResult

logger = logging.getLogger(__name__)


class ClinicalExtractorExecutor(Executor):
    """Executor that extracts clinical data from PA request documents.

    This is a wrapper around the existing ClinicalDataExtractor pipeline
    component, adapted for the Microsoft Agent Framework.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        use_mock: bool = True,
        id: str = "clinical_extractor",
    ):
        """Initialize the clinical extractor executor.

        Args:
            config: Configuration dict for the underlying extractor
            use_mock: If True, use mock extraction (for testing without Azure)
            id: Executor identifier
        """
        super().__init__(id=id)
        self._config = config or {}
        self._use_mock = use_mock
        self._extractor = None

    async def _ensure_extractor(self) -> Any:
        """Lazily initialize the extractor."""
        if self._extractor is None and not self._use_mock:
            try:
                from src.pipeline.clinicalExtractor.run import ClinicalDataExtractor

                self._extractor = ClinicalDataExtractor(**self._config)
            except ImportError:
                logger.warning(
                    "ClinicalDataExtractor not available, using mock extraction"
                )
                self._use_mock = True
        return self._extractor

    async def _mock_extract(self, request: PAProcessingRequest) -> ExtractionResult:
        """Perform mock extraction for testing."""
        logger.info(f"[{self.id}] Mock extraction for session: {request.session_id}")

        # Simulate extracted data based on input
        patient_data = {
            "name": "John Doe",
            "dob": "1985-03-15",
            "member_id": f"MBR-{request.session_id[:8]}",
            "gender": "Male",
        }

        physician_data = {
            "name": "Dr. Jane Smith",
            "npi": "1234567890",
            "specialty": "Orthopedics",
        }

        clinical_data = {
            "diagnoses": request.diagnosis_codes or ["M17.11"],  # Knee osteoarthritis
            "procedures": request.procedure_codes or ["27447"],  # Total knee replacement
            "clinical_notes": request.clinical_text[:200] if request.clinical_text else "Patient presents with chronic knee pain",
        }

        return ExtractionResult(
            session_id=request.session_id,
            patient_data=patient_data,
            physician_data=physician_data,
            clinical_data=clinical_data,
            raw_text=request.clinical_text,
        )

    @handler
    async def extract(
        self,
        request: PAProcessingRequest,
        ctx: WorkflowContext[ExtractionResult],
    ) -> None:
        """Extract clinical data from PA request.

        Args:
            request: The PA processing request containing clinical text
            ctx: Workflow context for sending messages to next executor
        """
        logger.info(f"[{self.id}] Processing extraction for session: {request.session_id}")

        if self._use_mock:
            result = await self._mock_extract(request)
        else:
            extractor = await self._ensure_extractor()
            # Call the real extractor
            raw_result = await extractor.run(
                # session_id=request.session_id,
                clinical_text=request.clinical_text,
            )
            result = ExtractionResult(
                session_id=request.session_id,
                patient_data=raw_result.get("patient_data", {}),
                physician_data=raw_result.get("physician_data", {}),
                clinical_data=raw_result.get("clinical_data", {}),
                raw_text=request.clinical_text,
            )

        logger.info(
            f"[{self.id}] Extraction complete. "
            f"Patient: {result.patient_data.get('name', 'Unknown')}, "
            f"Diagnoses: {result.clinical_data.get('diagnoses', [])}"
        )

        # Send result to next executor in the workflow
        await ctx.send_message(result)
