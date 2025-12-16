# Copyright (c) Microsoft. All rights reserved.
"""PA Determination Executor.

This executor generates the final Prior Authorization determination
based on clinical data and policy information.
"""

import logging
from typing import Any

from agent_framework import Executor, WorkflowContext, handler
from typing_extensions import Never

from src.agenticai.messages import PolicyRetrievalResult, DeterminationResult

logger = logging.getLogger(__name__)


class DeterminationExecutor(Executor):
    """Executor that generates the final PA determination.

    This wraps the existing AutoPADeterminator pipeline component,
    producing the final approval/denial decision with supporting evidence.
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        use_mock: bool = True,
        confidence_threshold: float = 0.85,
        id: str = "determination",
    ):
        """Initialize the determination executor.

        Args:
            config: Configuration dict for determination settings
            use_mock: If True, use mock determination (for testing without Azure)
            confidence_threshold: Threshold for auto-approval (0.0 to 1.0)
            id: Executor identifier
        """
        super().__init__(id=id)
        self._config = config or {}
        self._use_mock = use_mock
        self._confidence_threshold = confidence_threshold
        self._determinator = None

    async def _ensure_determinator(self) -> Any:
        """Lazily initialize the determinator."""
        if self._determinator is None and not self._use_mock:
            try:
                from src.pipeline.autoDetermination.run import AutoPADeterminator

                self._determinator = AutoPADeterminator(**self._config)
            except ImportError:
                logger.warning(
                    "AutoPADeterminator not available, using mock determination"
                )
                self._use_mock = True
        return self._determinator

    async def _mock_determine(
        self, retrieval: PolicyRetrievalResult
    ) -> DeterminationResult:
        """Perform mock determination for testing."""
        logger.info(f"[{self.id}] Mock determination for session: {retrieval.session_id}")

        # Simulate determination based on retrieval score
        if retrieval.evaluation_score >= self._confidence_threshold:
            decision = "approved"
            confidence = retrieval.evaluation_score
            reasoning = (
                "Prior Authorization APPROVED. "
                f"Policy evaluation score ({retrieval.evaluation_score:.2f}) meets threshold. "
                "Clinical documentation supports medical necessity criteria as defined in policy guidelines."
            )
            requires_review = False
        elif retrieval.evaluation_score >= 0.6:
            decision = "pending_review"
            confidence = retrieval.evaluation_score
            reasoning = (
                "Requires HUMAN REVIEW. "
                f"Policy evaluation score ({retrieval.evaluation_score:.2f}) is below auto-approval threshold. "
                "Additional clinical documentation may be needed to establish medical necessity."
            )
            requires_review = True
        else:
            decision = "denied"
            confidence = 1.0 - retrieval.evaluation_score
            reasoning = (
                "Prior Authorization DENIED. "
                f"Policy evaluation score ({retrieval.evaluation_score:.2f}) indicates insufficient evidence. "
                "Clinical documentation does not meet required medical necessity criteria."
            )
            requires_review = False

        # Collect supporting evidence from policies
        supporting_evidence = [
            f"Policy: {p.get('title', 'Unknown')} - {p.get('section', 'General')}"
            for p in retrieval.relevant_policies[:3]
        ]
        supporting_evidence.append(f"Evaluation reasoning: {retrieval.reasoning}")

        return DeterminationResult(
            session_id=retrieval.session_id,
            decision=decision,
            reasoning=reasoning,
            confidence_score=confidence,
            supporting_evidence=supporting_evidence,
            requires_human_review=requires_review,
        )

    @handler
    async def determine(
        self,
        retrieval: PolicyRetrievalResult,
        ctx: WorkflowContext[Never, DeterminationResult],
    ) -> None:
        """Generate final PA determination.

        Args:
            retrieval: Policy retrieval result with matched policies
            ctx: Workflow context for yielding final output
        """
        logger.info(f"[{self.id}] Generating determination for session: {retrieval.session_id}")

        if self._use_mock:
            result = await self._mock_determine(retrieval)
        else:
            determinator = await self._ensure_determinator()
            raw_result = await determinator.run(
                session_id=retrieval.session_id,
                policies=retrieval.relevant_policies,
            )
            result = DeterminationResult(
                session_id=retrieval.session_id,
                decision=raw_result.get("decision", "pending_review"),
                reasoning=raw_result.get("reasoning", ""),
                confidence_score=raw_result.get("confidence", 0.0),
                supporting_evidence=raw_result.get("evidence", []),
                requires_human_review=raw_result.get("requires_review", True),
            )

        logger.info(
            f"[{self.id}] Determination complete. "
            f"Decision: {result.decision}, Confidence: {result.confidence_score:.2f}"
        )

        # Yield the final output of the workflow
        await ctx.yield_output(result)
