"""Bounded deterministic and model-assisted review for research reports."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.context.citations.validity import check_citation_validity
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.orchestration.interfaces import GenerationRuntimeInterface
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.ai.runtime.generation.validation.runtime.enums import RuntimeType
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.synthesis.models import ResearchDraft

logger = structlog.get_logger()


class ReviewDecision(StrEnum):
    PASS = "pass"
    REVISE_SYNTHESIS = "revise_synthesis"
    FINALIZE_WITH_LIMITATIONS = "finalize_with_limitations"
    RESEARCH_GAPS = "research_gaps"
    FAIL = "fail"


class ResearchReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecision
    citation_integrity_score: float = Field(ge=0, le=1)
    completeness_score: float = Field(ge=0, le=1)
    revision_instructions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    gap_questions: list[str] = Field(default_factory=list, max_length=1)
    model_quality_score: float | None = Field(default=None, ge=0, le=1)


class ModelReviewAssessment(BaseModel):
    """Small, schema-bound opinion from the reviewer model.

    The model can identify one missing evidence question, but it cannot override
    deterministic citation integrity checks or request arbitrary tool work.
    """

    model_config = ConfigDict(extra="forbid")

    quality_score: float = Field(ge=0, le=1)
    gap_questions: list[str] = Field(default_factory=list, max_length=1)
    concerns: list[str] = Field(default_factory=list, max_length=4)


def review_draft(*, draft: ResearchDraft, evidence: ResearchEvidenceBundle) -> ResearchReview:
    """Choose the cheapest safe outcome from a bounded deterministic review."""

    used = set(draft.citation_ids)
    for finding in draft.findings:
        used.update(finding.citation_ids)
    citation_report = check_citation_validity(
        used_citation_ids=used,
        known_citation_ids=set(evidence.citation_ids),
    )
    if citation_report.unknown_citation_ids:
        return ResearchReview(
            decision=ReviewDecision.REVISE_SYNTHESIS,
            citation_integrity_score=0,
            completeness_score=0,
            revision_instructions=["Remove or replace unsupported citations."],
        )
    if evidence.citation_ids and not used:
        return ResearchReview(
            decision=ReviewDecision.REVISE_SYNTHESIS,
            citation_integrity_score=0,
            completeness_score=1,
            revision_instructions=[
                "Add citations from the supplied evidence to evidence-backed findings."
            ],
        )
    if evidence.completed_task_count == 0:
        return ResearchReview(
            decision=ReviewDecision.FAIL,
            citation_integrity_score=0,
            completeness_score=0,
            limitations=["No planned research task produced usable evidence."],
        )
    if evidence.failed_task_count:
        return ResearchReview(
            decision=ReviewDecision.FINALIZE_WITH_LIMITATIONS,
            citation_integrity_score=1,
            completeness_score=evidence.completed_task_count
            / (evidence.completed_task_count + evidence.failed_task_count),
            limitations=["One or more planned research tasks did not complete."],
        )
    return ResearchReview(
        decision=ReviewDecision.PASS,
        citation_integrity_score=1,
        completeness_score=1,
    )


class ResearchReviewService:
    """Combines deterministic checks with one bounded Generation Runtime review."""

    MAX_EVIDENCE_ITEMS = 12
    MAX_EXCERPT_CHARACTERS = 350

    def __init__(self, generation_runtime: GenerationRuntimeInterface) -> None:
        self._generation_runtime = generation_runtime

    async def review(
        self,
        *,
        goal: str,
        draft: ResearchDraft,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
        provider: GenerationProvider | None = None,
        routing_strategy: RoutingStrategy | None = None,
    ) -> ResearchReview:
        """Return the cheapest safe decision without letting model failure block a report."""

        deterministic = review_draft(draft=draft, evidence=evidence)
        if deterministic.decision in {ReviewDecision.FAIL, ReviewDecision.REVISE_SYNTHESIS}:
            return deterministic

        try:
            assessment = await self._model_review(
                goal=goal,
                draft=draft,
                evidence=evidence,
                owner_id=owner_id,
                research_run_id=research_run_id,
                provider=provider,
                routing_strategy=routing_strategy,
            )
        except Exception:
            # Deterministic review is still safe. Treat unavailable optional
            # review capacity as a visible limitation instead of retrying it.
            logger.warning(
                "research_runtime.review.model_review_unavailable",
                research_run_id=str(research_run_id),
            )
            return deterministic.model_copy(
                update={
                    "decision": ReviewDecision.FINALIZE_WITH_LIMITATIONS,
                    "limitations": [
                        *deterministic.limitations,
                        "Model-based review was unavailable; deterministic checks passed.",
                    ],
                }
            )

        if assessment.gap_questions:
            return deterministic.model_copy(
                update={
                    "decision": ReviewDecision.RESEARCH_GAPS,
                    "gap_questions": assessment.gap_questions,
                    "limitations": [*deterministic.limitations, *assessment.concerns],
                    "model_quality_score": assessment.quality_score,
                }
            )
        return deterministic.model_copy(
            update={
                "limitations": [*deterministic.limitations, *assessment.concerns],
                "model_quality_score": assessment.quality_score,
            }
        )

    async def _model_review(
        self,
        *,
        goal: str,
        draft: ResearchDraft,
        evidence: ResearchEvidenceBundle,
        owner_id: UUID,
        research_run_id: UUID,
        provider: GenerationProvider | None,
        routing_strategy: RoutingStrategy | None,
    ) -> ModelReviewAssessment:
        evidence_text = "\n".join(
            f"[{item.citation_id or 'uncited'}] {item.filename}: "
            f"{item.excerpt[: self.MAX_EXCERPT_CHARACTERS]}"
            for item in evidence.evidence[: self.MAX_EVIDENCE_ITEMS]
        )
        findings = "\n".join(
            f"- {section.heading}: {section.content[:500]}" for section in draft.findings
        )
        result = await self._generation_runtime.execute(
            GenerationRequest(
                prompt_context=PromptContext(context=evidence_text, chunks=[]),
                system_prompt=(
                    "Review a bounded research-report draft for evidence coverage. "
                    "Do not invent facts or citations. Return at most one narrowly "
                    "worded retrieval question only when supplied evidence cannot answer "
                    "a material part of the goal. An empty gap_questions list means no "
                    "additional retrieval is needed."
                ),
                user_prompt=(
                    f"Research goal: {goal}\n\nReport title: {draft.title}\n"
                    f"Abstract: {draft.abstract[:800]}\n\nFindings:\n{findings}\n\n"
                    "Assess coverage using only the supplied evidence."
                ),
                response_format=ResponseFormat.STRUCTURED,
                output_model=ModelReviewAssessment,
                max_tokens=400,
                max_regeneration_attempts=1,
                owner_id=owner_id,
                session_id=research_run_id,
                routing_strategy=routing_strategy,
                # NEVER-cached -- see the matching comment in
                # synthesis/service.py. A review verdict semantically
                # matched from a different run's evidence would be wrong,
                # not just stale.
                cache_runtime=CacheRuntime.REVIEWER,
                runtime=RuntimeType.REVIEWER,
                metadata={
                    "research_run_id": str(research_run_id),
                    "prompt_version": "research-review-v1",
                },
            ),
            provider=provider,
        )
        try:
            return (
                result.parsed_output
                if isinstance(result.parsed_output, ModelReviewAssessment)
                else ModelReviewAssessment.model_validate(result.parsed_output)
            )
        except Exception as exc:
            raise ValueError("Reviewer did not return a schema-valid assessment.") from exc
