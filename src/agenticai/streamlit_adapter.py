"""
Streamlit Adapter for Microsoft Agent Framework PA Workflow.

This module provides a bridge between the Streamlit UI and the new MAF-based
PA workflow, maintaining compatibility with the legacy PAProcessingPipeline
interface while using the new workflow infrastructure.
"""

import asyncio
import os
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import dotenv

from src.utils.ml_logging import get_logger

logger = get_logger()

dotenv.load_dotenv(".env", override=True)


class MAFPipelineAdapter:
    """
    Adapter that wraps the Microsoft Agent Framework PA workflow to provide
    the same interface as the legacy PAProcessingPipeline.
    
    This allows the Streamlit app to use either processing mode with minimal
    code changes.
    """

    def __init__(
        self,
        use_mock: bool = False,
        send_cloud_logs: bool = False,
    ) -> None:
        """
        Initialize the MAF Pipeline Adapter.
        
        Args:
            use_mock: If True, use mock implementations (no Azure calls)
            send_cloud_logs: If True, enable cloud logging (not yet implemented)
        """
        self.use_mock = use_mock
        self.send_cloud_logs = send_cloud_logs
        self.results: Dict[str, Dict[str, Any]] = {}
        self._workflow: Any = None  # Type: Workflow (lazy loaded)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of the workflow."""
        if self._initialized:
            return
            
        try:
            from src.agenticai.workflows.pa_workflow import create_pa_workflow
            
            self._workflow = create_pa_workflow(use_mock=self.use_mock)
            self._initialized = True
            logger.info("MAF PA workflow initialized successfully")
        except ImportError as e:
            logger.error(f"Failed to import agent_framework: {e}")
            raise RuntimeError(
                "Microsoft Agent Framework is not installed. "
                "Run: pip install agent-framework-azure-ai --pre"
            ) from e

    async def run(
        self,
        uploaded_files: List[str],
        streamlit: bool = False,
        caseId: Optional[str] = None,
        use_o1: bool = False,
    ) -> str:
        """
        Run the PA processing workflow using Microsoft Agent Framework.
        
        This method maintains the same interface as PAProcessingPipeline.run()
        for compatibility with the Streamlit app.
        
        Args:
            uploaded_files: List of file paths to process
            streamlit: Whether running in Streamlit context
            caseId: Optional case ID (generated if not provided)
            use_o1: Whether to use o1 model (passed to determination)
            
        Returns:
            The case ID for this processing run
        """
        self._ensure_initialized()
        
        case_id = caseId or str(uuid.uuid4())[:8]
        
        logger.info(f"[MAF] Starting PA workflow for case {case_id}")
        logger.info(f"[MAF] Processing {len(uploaded_files)} files")
        logger.info(f"[MAF] Use mock: {self.use_mock}, Use o1: {use_o1}")
        
        # Build clinical text from uploaded files
        clinical_text = await self._extract_text_from_files(uploaded_files)
        
        # Prepare the input request
        from src.agenticai.messages import PAProcessingRequest
        
        request = PAProcessingRequest(
            session_id=case_id,
            clinical_text=clinical_text,
            procedure_codes=[],  # Extracted during processing
            diagnosis_codes=[],   # Extracted during processing
            metadata={
                "uploaded_files": [os.path.basename(f) for f in uploaded_files],
                "use_o1": use_o1,
                "streamlit": streamlit,
            }
        )
        
        # Run the workflow
        try:
            result = await self._execute_workflow(request)
            
            # Transform result to legacy format for Streamlit compatibility
            legacy_result = self._transform_to_legacy_format(result, uploaded_files)
            self.results[case_id] = legacy_result
            
            logger.info(f"[MAF] Workflow completed for case {case_id}")
            return case_id
            
        except Exception as e:
            logger.error(f"[MAF] Workflow failed for case {case_id}: {e}")
            # Store error result
            self.results[case_id] = {
                "error": str(e),
                "pa_determination_results": f"Error processing PA request: {e}",
                "ocr_ner_results": self._get_empty_ocr_ner_results(),
                "agenticrag_results": {"policies": [], "evaluation_score": 0},
                "raw_uploaded_files": [os.path.basename(f) for f in uploaded_files],
            }
            raise

    async def _extract_text_from_files(self, file_paths: List[str]) -> str:
        """
        Extract text content from uploaded files.
        
        In mock mode, returns a placeholder. In production, would use
        Document Intelligence to extract text.
        """
        if self.use_mock:
            file_names = [os.path.basename(f) for f in file_paths]
            return f"[Mock extracted text from files: {', '.join(file_names)}]"
        
        # Production: Use Document Intelligence for OCR
        try:
            from src.documentintelligence.document_intelligence_helper import (
                AzureDocumentIntelligenceManager,
            )
            from src.extractors.pdfhandler import OCRHelper
            
            doc_intel = AzureDocumentIntelligenceManager()
            ocr_helper = OCRHelper()
            
            all_text = []
            for file_path in file_paths:
                if file_path.lower().endswith('.pdf'):
                    # Extract images from PDF and OCR
                    images = ocr_helper.extract_images_from_pdf(file_path)
                    for img_path in images:
                        result = doc_intel.analyze_document(img_path)
                        if hasattr(result, 'content') and result.content:
                            all_text.append(result.content)
                else:
                    # Direct OCR on image
                    result = doc_intel.analyze_document(file_path)
                    if hasattr(result, 'content') and result.content:
                        all_text.append(result.content)
            
            return "\n\n".join(all_text) if all_text else "[No text extracted]"
            
        except Exception as e:
            logger.warning(f"Failed to extract text from files: {e}")
            return f"[Failed to extract text: {e}]"

    async def _execute_workflow(self, request) -> Dict[str, Any]:
        """Execute the MAF workflow and return results."""
        from agent_framework import WorkflowOutputEvent
        
        # Convert request to dict for the workflow input
        request_dict = asdict(request)
        
        # Run the workflow using streaming API
        result_data = {}
        async for event in self._workflow.run_stream(request_dict):
            if isinstance(event, WorkflowOutputEvent):
                result_data = event.data
        
        return result_data if result_data else {}

    def _transform_to_legacy_format(
        self, 
        maf_result: Dict[str, Any],
        uploaded_files: List[str]
    ) -> Dict[str, Any]:
        """
        Transform MAF workflow output to legacy format expected by Streamlit.
        
        The legacy format includes:
        - ocr_ner_results: patient_info, physician_info, clinical_info
        - agenticrag_results: policies, evaluation_score
        - pa_determination_results: Final determination text
        - policy_location: List of policy sources
        - raw_uploaded_files: Original file names
        """
        # Extract components from MAF result
        extraction = maf_result.get("extraction", {})
        retrieval = maf_result.get("retrieval", {})
        determination = maf_result.get("determination", {})
        
        # Build OCR/NER results in legacy format
        ocr_ner_results = {
            "patient_info": extraction.get("patient_data", {
                "patient_name": "Not provided",
                "patient_date_of_birth": "Not provided",
                "patient_id": "Not provided",
                "patient_address": "Not provided",
                "patient_phone_number": "Not provided",
            }),
            "physician_info": extraction.get("physician_data", {
                "physician_name": "Not provided",
                "specialty": "Not provided",
                "physician_contact": {
                    "office_phone": "Not provided",
                    "fax": "Not provided",
                    "office_address": "Not provided",
                }
            }),
            "clinical_info": extraction.get("clinical_data", {
                "diagnosis": "Not provided",
                "icd_10_code": "Not provided",
                "prior_treatments_and_results": "Not provided",
                "specific_drugs_taken_and_failures": "Not provided",
                "alternative_drugs_required": "Not provided",
                "relevant_lab_results_or_imaging": "Not provided",
                "symptom_severity_and_impact": "Not provided",
                "prognosis_and_risk_if_not_approved": "Not provided",
                "clinical_rationale_for_urgency": "Not provided",
                "treatment_request": extraction.get("treatment_request", {
                    "name_of_medication_or_procedure": "Not provided",
                    "code_of_medication_or_procedure": "Not provided",
                    "dosage": "Not provided",
                    "duration": "Not provided",
                    "rationale": "Not provided",
                })
            }),
        }
        
        # Build agentic RAG results
        policies = retrieval.get("policies", [])
        policy_texts = [p.get("content", "") for p in policies] if isinstance(policies, list) else []
        
        agenticrag_results = {
            "policies": "\n\n".join(policy_texts) if policy_texts else "No policies retrieved",
            "evaluation_score": retrieval.get("evaluation_score", 0),
            "query_expansion": retrieval.get("expanded_queries", []),
        }
        
        # Build determination result
        decision = determination.get("decision", "pending_review")
        reasoning = determination.get("reasoning", "No reasoning provided")
        confidence = determination.get("confidence_score", 0)
        
        pa_determination_results = f"""
## Prior Authorization Determination

**Decision:** {decision.upper()}
**Confidence Score:** {confidence:.0%}

### Reasoning
{reasoning}

### Supporting Evidence
{chr(10).join(f'- {e}' for e in determination.get('supporting_evidence', []))}
"""
        
        return {
            "ocr_ner_results": ocr_ner_results,
            "agenticrag_results": agenticrag_results,
            "pa_determination_results": pa_determination_results,
            "pa_determination_results_md": pa_determination_results,  # Already markdown
            "policy_location": [p.get("source", "Unknown") for p in policies] if isinstance(policies, list) else [],
            "raw_uploaded_files": [os.path.basename(f) for f in uploaded_files],
            "maf_metadata": {
                "decision": decision,
                "confidence_score": confidence,
                "requires_human_review": determination.get("requires_human_review", False),
            }
        }

    def _get_empty_ocr_ner_results(self) -> Dict[str, Any]:
        """Return empty OCR/NER results structure."""
        return {
            "patient_info": {
                "patient_name": "Not provided",
                "patient_date_of_birth": "Not provided",
                "patient_id": "Not provided",
                "patient_address": "Not provided",
                "patient_phone_number": "Not provided",
            },
            "physician_info": {
                "physician_name": "Not provided",
                "specialty": "Not provided",
                "physician_contact": {
                    "office_phone": "Not provided",
                    "fax": "Not provided",
                    "office_address": "Not provided",
                }
            },
            "clinical_info": {
                "diagnosis": "Not provided",
                "icd_10_code": "Not provided",
                "prior_treatments_and_results": "Not provided",
                "treatment_request": {
                    "name_of_medication_or_procedure": "Not provided",
                    "code_of_medication_or_procedure": "Not provided",
                    "dosage": "Not provided",
                    "duration": "Not provided",
                    "rationale": "Not provided",
                }
            },
        }


# Convenience function to create the appropriate pipeline
def create_pa_pipeline(
    use_maf: bool = False,
    use_mock: bool = False,
    send_cloud_logs: bool = False,
):
    """
    Factory function to create the appropriate PA processing pipeline.
    
    Args:
        use_maf: If True, use Microsoft Agent Framework workflow
        use_mock: If True, use mock implementations (MAF only)
        send_cloud_logs: If True, enable cloud logging
        
    Returns:
        Either PAProcessingPipeline (legacy) or MAFPipelineAdapter (new)
    """
    if use_maf:
        logger.info("Creating MAF-based PA pipeline")
        return MAFPipelineAdapter(use_mock=use_mock, send_cloud_logs=send_cloud_logs)
    else:
        logger.info("Creating legacy PA pipeline")
        from src.pipeline.paprocessing.run import PAProcessingPipeline
        return PAProcessingPipeline(send_cloud_logs=send_cloud_logs)
