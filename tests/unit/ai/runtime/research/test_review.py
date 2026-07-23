from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.generation.caching.enums import CacheRuntime
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.review import (
    ModelReviewAssessment,
    ResearchReviewService,
    ReviewDecision,
    review_draft,
)
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection


def _draft() -> ResearchDraft:
    return ResearchDraft(
        title="Title",
        abstract="Abstract",
        methodology="Method",
        discussion="Discussion",
        conclusion="Conclusion",
        findings=[
            ResearchDraftSection(
                heading="Finding",
                content="Text",
                citation_ids=["c1"],
            )
        ],
        citation_ids=["c1"],
    )


def test_review_marks_failed_retrieval_as_limited() -> None:
    review = review_draft(
        draft=_draft(),
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=1
        ),
    )
    assert review.decision is ReviewDecision.FINALIZE_WITH_LIMITATIONS


def test_review_requests_synthesis_only_revision_when_citations_are_omitted() -> None:
    draft = _draft()
    draft = draft.model_copy(
        update={
            "citation_ids": [],
            "findings": [draft.findings[0].model_copy(update={"citation_ids": []})],
        }
    )
    review = review_draft(
        draft=draft,
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
    )
    assert review.decision is ReviewDecision.REVISE_SYNTHESIS
    assert review.revision_instructions


@pytest.mark.asyncio
async def test_model_reviewer_routes_only_a_bounded_targeted_gap_question() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ModelReviewAssessment(
            quality_score=0.6,
            gap_questions=["What benchmark evidence compares the alternatives?"],
            concerns=["The comparison is incomplete."],
        )
    )

    review = await ResearchReviewService(runtime).review(
        goal="Compare alternatives",
        draft=_draft(),
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )

    assert review.decision is ReviewDecision.RESEARCH_GAPS
    assert review.gap_questions == ["What benchmark evidence compares the alternatives?"]
    assert review.model_quality_score == 0.6


@pytest.mark.asyncio
async def test_model_review_is_never_cached_under_the_shared_research_answer_namespace() -> None:
    """Regression test: a model-based review verdict must not share
    `CacheRuntime.RESEARCH` (AUTO, semantic-matched) with Linear Research
    answers -- a semantic-cache hit would return a verdict computed against
    a *different* run's draft/evidence. See PRODUCT_FLOWS_AND_GAPS.md
    Loophole D1."""

    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=ModelReviewAssessment(quality_score=0.9, gap_questions=[], concerns=[])
    )
    await ResearchReviewService(runtime).review(
        goal="q",
        draft=_draft(),
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    request = runtime.execute.await_args.args[0]
    assert request.cache_runtime == CacheRuntime.REVIEWER
    assert request.cache_runtime != CacheRuntime.RESEARCH


@pytest.mark.asyncio
async def test_model_reviewer_does_not_run_when_deterministic_citation_check_fails() -> None:
    runtime = AsyncMock()
    invalid = _draft().model_copy(update={"citation_ids": ["invented"]})

    review = await ResearchReviewService(runtime).review(
        goal="q",
        draft=invalid,
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )

    assert review.decision is ReviewDecision.REVISE_SYNTHESIS
    runtime.execute.assert_not_awaited()
