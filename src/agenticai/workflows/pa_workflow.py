# Copyright (c) Microsoft. All rights reserved.
"""Prior Authorization Workflow using Microsoft Agent Framework.

This module defines the end-to-end PA processing workflow that can be
discovered and tested via DevUI.

Workflow Flow:
    PAProcessingRequest → ClinicalExtractor → AgenticRAG → Determination → DeterminationResult

Usage:
    # Via DevUI CLI (from project root)
    devui ./src/agenticai/devui_entities --port 8080

    # Via Python
    from agent_framework.devui import serve
    from src.agenticai.workflows import workflow
    serve(entities=[workflow], port=8080, auto_open=True)
"""

import logging

from agent_framework import WorkflowBuilder, Workflow

from src.agenticai.executors import (
    ClinicalExtractorExecutor,
    AgenticRAGExecutor,
    DeterminationExecutor,
)

logger = logging.getLogger(__name__)


def create_pa_workflow(
    use_mock: bool = False,
    confidence_threshold: float = 0.85,
) -> Workflow:
    """Create the Prior Authorization processing workflow.

    This workflow chains three executors:
    1. ClinicalExtractorExecutor - Extracts patient/physician/clinical data
    2. AgenticRAGExecutor - Retrieves and evaluates relevant policies
    3. DeterminationExecutor - Generates final PA decision

    Args:
        use_mock: If True, use mock implementations (no Azure required)
        confidence_threshold: Threshold for auto-approval decisions

    Returns:
        Configured Workflow instance ready for execution
    """
    logger.info("Creating Prior Authorization Workflow...")

    # Create executor instances
    clinical_extractor = ClinicalExtractorExecutor(
        use_mock=use_mock,
        id="clinical_extractor",
    )

    agentic_rag = AgenticRAGExecutor(
        use_mock=use_mock,
        id="agentic_rag",
    )

    determination = DeterminationExecutor(
        use_mock=use_mock,
        confidence_threshold=confidence_threshold,
        id="determination",
    )

    # Build the workflow using WorkflowBuilder
    workflow = (
        WorkflowBuilder(
            name="Prior Authorization Workflow",
            description=(
                "End-to-end Prior Authorization processing pipeline. "
                "Extracts clinical data, retrieves relevant policies, "
                "and generates PA determination decisions."
            ),
        )
        # Set the entry point
        .set_start_executor(clinical_extractor)
        # Chain executors: Extract → RAG → Determine
        .add_edge(clinical_extractor, agentic_rag)
        .add_edge(agentic_rag, determination)
        # Build the workflow
        .build()
    )

    logger.info(
        f"Created workflow with executors: "
        f"{clinical_extractor.id} → {agentic_rag.id} → {determination.id}"
    )

    return workflow


# Create the default workflow instance for DevUI discovery
# DevUI looks for a module-level 'workflow' variable
workflow = create_pa_workflow(use_mock=True)


# Entry point for running with DevUI
def main():
    """Launch the PA workflow in DevUI."""
    from agent_framework.devui import serve

    # Setup logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("Starting Prior Authorization Workflow in DevUI")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Available at: http://localhost:8080")
    logger.info("")
    logger.info("Workflow: Prior Authorization Processing")
    logger.info("  - clinical_extractor: Extract patient/clinical data")
    logger.info("  - agentic_rag: Retrieve and evaluate policies")
    logger.info("  - determination: Generate PA decision")
    logger.info("")
    logger.info("Input Format (PAProcessingRequest):")
    logger.info("  - session_id: Unique session identifier")
    logger.info("  - clinical_text: Clinical notes to process")
    logger.info("  - procedure_codes: List of CPT/HCPCS codes")
    logger.info("  - diagnosis_codes: List of ICD-10 codes")
    logger.info("=" * 60)

    # Launch DevUI server
    serve(entities=[workflow], port=8080, auto_open=True)


if __name__ == "__main__":
    main()
