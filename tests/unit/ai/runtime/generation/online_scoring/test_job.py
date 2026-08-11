"""
Unit tests for `OnlineScoringJob` (E5, EVALUATION_PLAN.md §14).

Repositories/artifact reader are mocked at the boundary, matching
tests/unit/services/test_feedback_service.py's convention -- no live DB,
no live LLM call, no live storage. `GenerationArtifactBuilder` builds
real `GenerationArtifact` fixtures from a real `GenerationResult` so the
job exercises its actual field access paths (`request.prompt_context`,
`response.content`, ...) rather than a hand-rolled stand-in.
"""

from __future__ import annotations

import random
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.online_scoring.job import OnlineScoringJob
from app.ai.runtime.generation.online_scoring.sampling import OnlineScoringConfig
from app.ai.runtime.research.review import ReviewDecision
from app.models.enums import EvalScoreSource
from app.models.generation_usage import GenerationUsage
from app.models.research_run import ResearchRun


def _make_context_chunk(*, citation_id: str = "S1") -> ContextChunk:
    return ContextChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="paper.pdf",
        owner_id=str(uuid.uuid4()),
        chunk_index=0,
        content="RAG combines retrieval with generation.",
        score=0.9,
        citation_id=citation_id,
    )


def _make_artifact_result(
    *,
    owner_id: uuid.UUID,
    generation_id: uuid.UUID | None = None,
    content: str = "RAG is retrieval-augmented generation [S1].",
    chunks: list[ContextChunk] | None = None,
    citations: list[Citation] | None = None,
    guardrails: GuardrailReport | None = None,
) -> GenerationResult:
    chunks = chunks if chunks is not None else [_make_context_chunk()]
    citations = (
        citations
        if citations is not None
        else [
            Citation(
                citation_id="S1",
                filename="paper.pdf",
                document_id=chunks[0].document_id if chunks else uuid.uuid4(),
            )
        ]
    )
    request = GenerationRequest(
        prompt_context=PromptContext(context="context", chunks=chunks, citations=citations),
        user_prompt="What is RAG?",
        owner_id=owner_id,
        surface="chat",
        prompt_version="chat-v1",
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content=content,
        guardrails=guardrails,
    )
    if generation_id is not None:
        result.generation_id = generation_id
    return result


def _make_usage_row(
    *,
    owner_id: uuid.UUID,
    generation_id: uuid.UUID | None = None,
    surface: str = "chat",
    guardrail_final_action: str | None = None,
    prompt_version: str | None = None,
    session_id: uuid.UUID | None = None,
) -> GenerationUsage:
    return GenerationUsage(
        request_id=uuid.uuid4(),
        generation_id=generation_id or uuid.uuid4(),
        owner_id=owner_id,
        provider="groq",
        model="test-model",
        surface=surface,
        guardrail_final_action=guardrail_final_action,
        prompt_version=prompt_version,
        session_id=session_id,
    )


def _guardrail_report(*, final_action: GuardrailAction) -> GuardrailReport:
    stage_result = GuardrailResult(
        stage=GuardrailStage.GENERATION, passed=True, blocked=False, action=GuardrailAction.ALLOW
    )
    return GuardrailReport(
        input_result=stage_result,
        retrieval_result=stage_result,
        generation_result=stage_result,
        final_action=final_action,
        blocked=False,
    )


class _JobHarness:
    """Wires an `OnlineScoringJob` with mocked repositories/reader and
    exposes the recorded `EvalScoreRepository.record()` calls for
    assertions, matching the MagicMock/AsyncMock convention in
    tests/unit/services/test_feedback_service.py."""

    def __init__(self, *, config: OnlineScoringConfig | None = None) -> None:
        self.generation_usage_repository = MagicMock()
        self.eval_score_repository = MagicMock()
        self.eval_score_repository.record = AsyncMock()
        self.research_run_repository = MagicMock()
        self.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=None)
        self.artifact_reader = MagicMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

        self.job = OnlineScoringJob(
            generation_usage_repository=self.generation_usage_repository,
            eval_score_repository=self.eval_score_repository,
            research_run_repository=self.research_run_repository,
            artifact_reader=self.artifact_reader,
            config=config or OnlineScoringConfig(baseline_sample_rate=0.0),
            commit=self.commit,
            rollback=self.rollback,
            rng=random.Random(0),
        )

    def record_calls(self) -> list[dict[str, object]]:
        return [call.kwargs for call in self.eval_score_repository.record.await_args_list]


@pytest.mark.asyncio
async def test_run_once_returns_zero_when_there_are_no_candidates() -> None:
    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[])

    processed = await harness.job.run_once()

    assert processed == 0
    harness.eval_score_repository.record.assert_not_awaited()


@pytest.mark.asyncio
async def test_scores_citation_validity_for_every_candidate_regardless_of_sampling() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    processed = await harness.job.run_once()

    assert processed == 1
    calls = harness.record_calls()
    assert len(calls) == 1
    assert calls[0]["metric_name"] == "citation_validity"
    assert calls[0]["passed"] is True
    assert calls[0]["source"] == EvalScoreSource.ONLINE_SAMPLED.value
    harness.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_flags_a_fabricated_citation_via_the_free_check() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            content="This claim cites a source that was never retrieved [S9].",
        )
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = harness.record_calls()
    citation_call = next(c for c in calls if c["metric_name"] == "citation_validity")
    assert citation_call["passed"] is False
    score = citation_call["score"]
    assert isinstance(score, float)
    assert score < 1.0


@pytest.mark.asyncio
async def test_missing_artifact_is_skipped_without_raising() -> None:
    owner_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id)

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(side_effect=ArtifactNotFoundError("missing"))

    processed = await harness.job.run_once()

    assert processed == 1
    harness.eval_score_repository.record.assert_not_awaited()
    harness.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_guardrail_flagged_row_is_sampled_for_judges_even_at_zero_baseline() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(
        owner_id=owner_id,
        generation_id=generation_id,
        guardrail_final_action=GuardrailAction.WARN.value,
    )
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    score_generation_fn = AsyncMock(
        return_value=MagicMock(
            checks=[
                MagicMock(metric="answer_relevancy", score=0.9, passed=True, reason="good"),
            ]
        )
    )
    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.job = OnlineScoringJob(
        generation_usage_repository=harness.generation_usage_repository,
        eval_score_repository=harness.eval_score_repository,
        research_run_repository=harness.research_run_repository,
        artifact_reader=harness.artifact_reader,
        config=OnlineScoringConfig(baseline_sample_rate=0.0),
        commit=harness.commit,
        rollback=harness.rollback,
        score_generation_fn=score_generation_fn,
        judge=object(),
        rng=random.Random(0),
    )

    await harness.job.run_once()

    score_generation_fn.assert_awaited_once()
    metric_names = {c["metric_name"] for c in harness.record_calls()}
    assert "citation_validity" in metric_names
    assert "answer_relevancy" in metric_names


@pytest.mark.asyncio
async def test_sampled_for_judges_but_no_judge_configured_only_writes_the_free_check() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(
        owner_id=owner_id,
        generation_id=generation_id,
        guardrail_final_action=GuardrailAction.WARN.value,
    )
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    metric_names = {c["metric_name"] for c in harness.record_calls()}
    assert metric_names == {"citation_validity"}


@pytest.mark.asyncio
async def test_not_sampled_row_never_calls_the_judge_function() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    score_generation_fn = AsyncMock()
    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.job = OnlineScoringJob(
        generation_usage_repository=harness.generation_usage_repository,
        eval_score_repository=harness.eval_score_repository,
        research_run_repository=harness.research_run_repository,
        artifact_reader=harness.artifact_reader,
        config=OnlineScoringConfig(baseline_sample_rate=0.0),
        commit=harness.commit,
        rollback=harness.rollback,
        score_generation_fn=score_generation_fn,
        judge=object(),
        rng=random.Random(0),
    )

    await harness.job.run_once()

    score_generation_fn.assert_not_awaited()


@pytest.mark.asyncio
async def test_deep_research_non_pass_review_decision_is_sampled_for_judges() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _make_usage_row(
        owner_id=owner_id,
        generation_id=generation_id,
        surface="deep_research",
        session_id=run_id,
    )
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run = ResearchRun(
        id=run_id,
        owner_id=owner_id,
        graph_thread_id=str(uuid.uuid4()),
        status="completed",
        budget_usage={"review_decision": ReviewDecision.REVISE_SYNTHESIS.value},
    )

    score_generation_fn = AsyncMock(
        return_value=MagicMock(
            checks=[MagicMock(metric="answer_relevancy", score=0.9, passed=True, reason="good")]
        )
    )
    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=run)
    harness.job = OnlineScoringJob(
        generation_usage_repository=harness.generation_usage_repository,
        eval_score_repository=harness.eval_score_repository,
        research_run_repository=harness.research_run_repository,
        artifact_reader=harness.artifact_reader,
        config=OnlineScoringConfig(baseline_sample_rate=0.0),
        commit=harness.commit,
        rollback=harness.rollback,
        score_generation_fn=score_generation_fn,
        judge=object(),
        rng=random.Random(0),
    )

    await harness.job.run_once()

    score_generation_fn.assert_awaited_once()
    harness.research_run_repository.get_by_id_for_owner.assert_awaited_once_with(
        run_id=run_id, owner_id=owner_id
    )


@pytest.mark.asyncio
async def test_chat_row_never_looks_up_a_research_run() -> None:
    owner_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, surface="chat")
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=row.generation_id)
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    harness.research_run_repository.get_by_id_for_owner.assert_not_awaited()


@pytest.mark.asyncio
async def test_a_failing_row_is_rolled_back_and_does_not_stop_the_batch() -> None:
    owner_id = uuid.uuid4()
    good_row = _make_usage_row(owner_id=owner_id)
    bad_row = _make_usage_row(owner_id=owner_id)
    good_artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=good_row.generation_id)
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(
        return_value=[bad_row, good_row]
    )
    harness.artifact_reader.read = AsyncMock(
        side_effect=[RuntimeError("storage exploded"), good_artifact]
    )

    processed = await harness.job.run_once()

    assert processed == 2
    harness.rollback.assert_awaited_once()
    harness.commit.assert_awaited_once()
    calls = harness.record_calls()
    assert len(calls) == 1
