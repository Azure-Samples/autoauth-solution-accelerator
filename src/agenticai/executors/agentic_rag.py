# Copyright (c) Microsoft. All rights reserved.
"""Agentic RAG Executor.

This executor handles query expansion and policy retrieval using
the Retrieval-Augmented Generation pattern.
"""

import logging
from typing import Any

from agent_framework import Executor, WorkflowContext, handler

from src.agenticai.messages import ExtractionResult, PolicyRetrievalResult

logger = logging.getLogger(__name__)


class AgenticRAGExecutor(Executor):
    """Executor that performs query expansion and policy retrieval.

    This wraps the existing AgenticRAG pipeline component, providing:
    - Query expansion from clinical data
    - Policy document retrieval from Azure AI Search
    - Relevance evaluation
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        use_mock: bool = True,
        id: str = "agentic_rag",
    ):
        """Initialize the agentic RAG executor.

        Args:
            config: Configuration dict for RAG settings
            use_mock: If True, use mock retrieval (for testing without Azure)
            id: Executor identifier
        """
        super().__init__(id=id)
        self._config = config or {}
        self._use_mock = use_mock
        self._rag = None

    async def _ensure_rag(self) -> Any:
        """Lazily initialize the RAG component."""
        if self._rag is None and not self._use_mock:
            try:
                from src.pipeline.agenticRag.run import AgenticRAG

                self._rag = AgenticRAG(**self._config)
            except ImportError:
                logger.warning("AgenticRAG not available, using mock retrieval")
                self._use_mock = True
        return self._rag

    async def _mock_retrieve(self, extraction: ExtractionResult) -> PolicyRetrievalResult:
        """Perform mock policy retrieval for testing."""
        logger.info(f"[{self.id}] Mock policy retrieval for session: {extraction.session_id}")

        diagnoses = extraction.clinical_data.get("diagnoses", [])
        procedures = extraction.clinical_data.get("procedures", [])

        # Simulate policy retrieval results
        relevant_policies = [
            {
                "policy_id": "POL-001",
                "title": "Total Knee Arthroplasty Medical Policy",
                "section": "Coverage Criteria",
                "content": (
                    "Total knee arthroplasty is considered medically necessary when: "
                    "1) Conservative treatment has failed for at least 3 months, "
                    "2) Radiographic evidence shows advanced joint disease, "
                    "3) Significant functional impairment is documented."
                ),
                "relevance_score": 0.92,
            },
            {
                "policy_id": "POL-002",
                "title": "Prior Authorization Requirements",
                "section": "Documentation",
                "content": (
                    "Required documentation includes: operative report, "
                    "imaging studies, conservative treatment history, "
                    "and functional assessment scores."
                ),
                "relevance_score": 0.87,
            },
        ]

        query_expansions = [
            f"knee replacement surgery requirements for {diagnoses[0] if diagnoses else 'osteoarthritis'}",
            f"medical necessity criteria for procedure {procedures[0] if procedures else '27447'}",
            "orthopedic surgery prior authorization policy",
        ]

        return PolicyRetrievalResult(
            session_id=extraction.session_id,
            relevant_policies=relevant_policies,
            evaluation_score=0.89,
            reasoning=(
                f"Found {len(relevant_policies)} relevant policies matching "
                f"diagnoses {diagnoses} and procedures {procedures}. "
                "Policies cover medical necessity criteria and documentation requirements."
            ),
            query_expansions=query_expansions,
        )

    @handler
    async def retrieve_policies(
        self,
        extraction: ExtractionResult,
        ctx: WorkflowContext[PolicyRetrievalResult],
    ) -> None:
        """Retrieve relevant policies based on extracted clinical data.

        Args:
            extraction: Extraction result from clinical extractor
            ctx: Workflow context for sending messages to next executor
        """
        logger.info(f"[{self.id}] Starting policy retrieval for session: {extraction.session_id}")

        if self._use_mock:
            result = await self._mock_retrieve(extraction)
        else:
            rag = await self._ensure_rag()
            raw_result = await rag.run(
                session_id=extraction.session_id,
                clinical_data=extraction.clinical_data,
            )
            result = PolicyRetrievalResult(
                session_id=extraction.session_id,
                relevant_policies=raw_result.get("policies", []),
                evaluation_score=raw_result.get("score", 0.0),
                reasoning=raw_result.get("reasoning", ""),
                query_expansions=raw_result.get("query_expansions", []),
            )

        logger.info(
            f"[{self.id}] Retrieved {len(result.relevant_policies)} policies. "
            f"Evaluation score: {result.evaluation_score:.2f}"
        )

        # Send result to next executor
        await ctx.send_message(result)
