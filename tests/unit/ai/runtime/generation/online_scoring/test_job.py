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
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.services.formatting import format_memory_context
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.online_scoring.job import (
    _GENERIC_ONLINE_RUBRIC,
    TOOL_INVOCATION_METRIC_NAMES,
    MemoryUtilityJudge,
    OnlineScoringJob,
)
from app.ai.runtime.generation.online_scoring.memory_utility import MemoryUtilityScore
from app.ai.runtime.generation.online_scoring.sampling import OnlineScoringConfig
from app.ai.runtime.research.review import ReviewDecision
from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
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
    metadata: dict[str, object] | None = None,
    context_text: str = "context",
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
        prompt_context=PromptContext(context=context_text, chunks=chunks, citations=citations),
        user_prompt="What is RAG?",
        owner_id=owner_id,
        surface="chat",
        prompt_version="chat-v1",
        metadata=metadata or {},
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

    def __init__(
        self,
        *,
        config: OnlineScoringConfig | None = None,
        memory_utility_judge: MemoryUtilityJudge | None = None,
    ) -> None:
        self.generation_usage_repository = MagicMock()
        # Default: no LangSmith run configured for this generation -- most
        # tests here aren't about the LangSmith sync, so this keeps
        # _sync_to_langsmith() a deterministic no-op unless a test opts in
        # by overriding this return value.
        self.generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=None)
        self.eval_score_repository = MagicMock()
        self.eval_score_repository.record = AsyncMock(return_value=None)
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
            memory_utility_judge=memory_utility_judge,
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
async def test_run_once_snapshots_entire_batch_before_per_row_commit() -> None:
    owner_id = uuid.uuid4()
    first_id = uuid.uuid4()
    second_id = uuid.uuid4()
    first = _make_usage_row(owner_id=owner_id, generation_id=first_id)
    second = _make_usage_row(owner_id=owner_id, generation_id=second_id)
    artifacts = {
        first_id: GenerationArtifactBuilder().build(
            result=_make_artifact_result(owner_id=owner_id, generation_id=first_id)
        ),
        second_id: GenerationArtifactBuilder().build(
            result=_make_artifact_result(owner_id=owner_id, generation_id=second_id)
        ),
    }
    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(
        return_value=[first, second]
    )
    harness.artifact_reader.read = AsyncMock(
        side_effect=lambda generation_id: artifacts[generation_id]
    )

    async def expire_remaining_rows() -> None:
        if harness.commit.await_count == 1:
            second.generation_id = uuid.uuid4()
            second.owner_id = uuid.uuid4()

    harness.commit.side_effect = expire_remaining_rows

    processed = await harness.job.run_once()

    assert processed == 2
    assert [call.args[0] for call in harness.artifact_reader.read.await_args_list] == [
        first_id,
        second_id,
    ]
    assert harness.rollback.await_count == 0


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
async def test_sampled_memory_backed_generation_records_utility_without_raw_text() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    memory = MemoryRecord(
        id=uuid.uuid4(),
        owner_id=owner_id,
        type=MemoryType.USER,
        content="Prefers concise answers",
        importance_score=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    memory_text = format_memory_context(MemoryContext(user_memories=[memory]))
    assert memory_text is not None
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    row.injected_memory_ids = [memory.id]
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            context_text=memory_text,
            metadata={"injected_memory_ids": [str(memory.id)]},
        )
    )
    judge = MagicMock()
    judge.evaluate = AsyncMock(
        return_value=MemoryUtilityScore(utility=0.8, relevant=True, harmful=False)
    )
    harness = _JobHarness(
        config=OnlineScoringConfig(baseline_sample_rate=1.0), memory_utility_judge=judge
    )
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = {call["metric_name"]: call for call in harness.record_calls()}
    assert calls["memory_utility"]["score"] == 0.8
    assert calls["memory_utility"]["reason"] == "memory relevant"
    assert calls["irrelevant_memory_harm"]["score"] == 0.0
    assert memory.content not in str(calls)


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
        completed_at=datetime.now(UTC),
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
    # Fetched once for a deep_research row (`_deep_research_run_for()`),
    # backing the terminal-status gate, review_decision, and the
    # web-search signal all together -- see that method's own docstring.
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


@pytest.mark.asyncio
async def test_failure_logging_does_not_read_an_expired_generation_id() -> None:
    """A failed transaction may expire ORM attributes before the handler logs."""

    row = _make_usage_row(owner_id=uuid.uuid4())
    generation_id = row.generation_id
    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])

    async def fail_after_expiring_row(_: GenerationUsage) -> None:
        row.__dict__.pop("generation_id", None)
        raise RuntimeError("original scoring failure")

    harness.job._score_one = fail_after_expiring_row  # type: ignore[assignment]

    processed = await harness.job.run_once()

    assert processed == 1
    assert generation_id is not None
    harness.rollback.assert_awaited_once()


def _fake_eval_score(*, metric_name: str, score: float, reason: str) -> EvalScore:
    return EvalScore(
        id=uuid.uuid4(),
        metric_name=metric_name,
        score=score,
        reason=reason,
        source=EvalScoreSource.ONLINE_SAMPLED.value,
    )


@pytest.mark.asyncio
async def test_syncs_the_free_check_to_langsmith_when_a_run_id_is_known() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run_id = uuid.uuid4()
    stored_score = _fake_eval_score(
        metric_name="citation_validity", score=1.0, reason="all citation checks passed"
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=run_id)
    harness.eval_score_repository.record = AsyncMock(return_value=stored_score)

    with patch("app.ai.runtime.generation.online_scoring.job.sync_eval_score") as sync_mock:
        await harness.job.run_once()

    sync_mock.assert_called_once_with(
        run_id=run_id,
        eval_score_id=stored_score.id,
        metric_name="citation_validity",
        score=1.0,
        reason="all citation checks passed",
    )


@pytest.mark.asyncio
async def test_does_not_sync_to_langsmith_when_no_run_id_is_known() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    # get_langsmith_run_id already defaults to None in _JobHarness.
    harness.eval_score_repository.record = AsyncMock(
        return_value=_fake_eval_score(metric_name="citation_validity", score=1.0, reason="ok")
    )

    with patch("app.ai.runtime.generation.online_scoring.job.sync_eval_score") as sync_mock:
        await harness.job.run_once()

    sync_mock.assert_not_called()


@pytest.mark.asyncio
async def test_does_not_sync_to_langsmith_when_record_returns_none() -> None:
    """`record()` returns `None` when `on_conflict_do_nothing` no-op'd --
    nothing new was written, so nothing new should be synced either."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=uuid.uuid4())
    harness.eval_score_repository.record = AsyncMock(return_value=None)

    with patch("app.ai.runtime.generation.online_scoring.job.sync_eval_score") as sync_mock:
        await harness.job.run_once()

    sync_mock.assert_not_called()


@pytest.mark.asyncio
async def test_syncs_every_judge_metric_to_langsmith_separately() -> None:
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
    run_id = uuid.uuid4()

    score_generation_fn = AsyncMock(
        return_value=MagicMock(
            checks=[MagicMock(metric="answer_relevancy", score=0.9, passed=True, reason="good")]
        )
    )
    harness = _JobHarness(config=OnlineScoringConfig(baseline_sample_rate=0.0))
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=run_id)
    harness.eval_score_repository.record = AsyncMock(
        side_effect=[
            _fake_eval_score(metric_name="citation_validity", score=1.0, reason="ok"),
            _fake_eval_score(metric_name="answer_relevancy", score=0.9, reason="good"),
        ]
    )
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

    with patch("app.ai.runtime.generation.online_scoring.job.sync_eval_score") as sync_mock:
        await harness.job.run_once()

    assert sync_mock.call_count == 2
    synced_metrics = {call.kwargs["metric_name"] for call in sync_mock.call_args_list}
    assert synced_metrics == {"citation_validity", "answer_relevancy"}


@pytest.mark.asyncio
async def test_optional_judge_failure_preserves_deterministic_scores_and_stops_retry() -> None:
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
    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    score_generation_fn = AsyncMock(side_effect=RuntimeError("provider included sensitive text"))
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

    processed = await harness.job.run_once()

    assert processed == 1
    calls = harness.record_calls()
    assert [call["metric_name"] for call in calls] == [
        "citation_validity",
        "online_judge_execution",
    ]
    assert calls[-1]["reason"] == "judge failed: RuntimeError"
    assert "sensitive text" not in str(calls)
    harness.commit.assert_awaited_once()
    harness.rollback.assert_not_awaited()


# ==============================================================
# E16 follow-up: rubric judge on online-sampled traffic (2026-08-12)
# ==============================================================


@pytest.mark.asyncio
async def test_rubric_judge_wired_and_sampled_passes_the_generic_rubric() -> None:
    """When a rubric_judge is configured (Settings.
    eval_online_rubric_judge_enabled) and the row is sampled for judges,
    the fixed generic rubric -- not a per-example one, online traffic has
    no such thing -- must be passed through to score_generation_fn."""

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
            checks=[MagicMock(metric="answer_relevancy", score=0.9, passed=True, reason="good")]
        )
    )
    rubric_judge = object()
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
        rubric_judge=rubric_judge,
        rng=random.Random(0),
    )

    await harness.job.run_once()

    assert score_generation_fn.await_args is not None
    call_kwargs = score_generation_fn.await_args.kwargs
    assert call_kwargs["rubric"] == _GENERIC_ONLINE_RUBRIC
    assert call_kwargs["rubric_judge"] is rubric_judge


@pytest.mark.asyncio
async def test_rubric_judge_not_configured_passes_no_rubric() -> None:
    """Default shape (rubric_judge=None, e.g. Settings.
    eval_online_rubric_judge_enabled is False) -- must not pass a rubric
    at all, so score_generation() takes its own no-op path rather than
    this job inventing a rubric with no judge to check it."""

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
            checks=[MagicMock(metric="answer_relevancy", score=0.9, passed=True, reason="good")]
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

    assert score_generation_fn.await_args is not None
    call_kwargs = score_generation_fn.await_args.kwargs
    assert call_kwargs["rubric"] is None
    assert call_kwargs["rubric_judge"] is None


@pytest.mark.asyncio
async def test_rubric_adherence_score_is_persisted_and_synced_like_any_other_metric() -> None:
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
                MagicMock(
                    metric="rubric_adherence",
                    score=0.0,
                    passed=False,
                    reason="misses the required tone",
                ),
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
        rubric_judge=object(),
        rng=random.Random(0),
    )

    await harness.job.run_once()

    calls = harness.record_calls()
    rubric_call = next(c for c in calls if c["metric_name"] == "rubric_adherence")
    assert rubric_call["passed"] is False
    assert rubric_call["reason"] == "misses the required tone"
    assert rubric_call["source"] == EvalScoreSource.ONLINE_SAMPLED.value


# ==============================================================
# E23: tool-invocation rate & success rate (EVALUATION_PLAN.md §10)
# ==============================================================


@pytest.mark.asyncio
async def test_tool_invocation_metrics_absent_from_metadata_are_not_recorded() -> None:
    """Linear Research/Deep Research generations, and Chat turns where
    both toggles were off, carry no tool-invocation keys at all -- must
    not appear as a False/0.0 row, just not recorded."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    metric_names = {c["metric_name"] for c in harness.record_calls()}
    assert metric_names.isdisjoint(TOOL_INVOCATION_METRIC_NAMES)


@pytest.mark.asyncio
async def test_web_search_invoked_and_succeeded_records_both_metrics_as_passed() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            metadata={"web_search_invoked": True, "web_search_success": True},
        )
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["web_search_invoked"]["passed"] is True
    assert calls["web_search_invoked"]["score"] == 1.0
    assert calls["web_search_success"]["passed"] is True
    assert calls["web_search_success"]["score"] == 1.0
    assert "paper_search_invoked" not in calls


@pytest.mark.asyncio
async def test_web_search_invoked_but_unsuccessful_records_a_failing_success_metric() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            metadata={"web_search_invoked": True, "web_search_success": False},
        )
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["web_search_invoked"]["passed"] is True
    assert calls["web_search_success"]["passed"] is False
    assert calls["web_search_success"]["score"] == 0.0


@pytest.mark.asyncio
async def test_toggled_on_but_not_invoked_records_only_the_invocation_metric() -> None:
    """Toggle was on this turn (so `web_search_invoked` is a meaningful
    question) but the necessity check decided against it -- `invoked`
    is `False`, and there is no `web_search_success` key at all (success
    is meaningless for a search that never ran)."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            metadata={"web_search_invoked": False},
        )
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["web_search_invoked"]["passed"] is False
    assert calls["web_search_invoked"]["score"] == 0.0
    assert "web_search_success" not in calls


@pytest.mark.asyncio
async def test_paper_search_metrics_are_recorded_independently_of_web_search() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            metadata={"paper_search_invoked": True, "paper_search_success": True},
        )
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["paper_search_invoked"]["passed"] is True
    assert calls["paper_search_success"]["passed"] is True
    assert "web_search_invoked" not in calls


@pytest.mark.asyncio
async def test_tool_invocation_metrics_are_synced_to_langsmith() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    row = _make_usage_row(owner_id=owner_id, generation_id=generation_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(
            owner_id=owner_id,
            generation_id=generation_id,
            metadata={"web_search_invoked": True, "web_search_success": True},
        )
    )
    run_id = uuid.uuid4()

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=run_id)
    harness.eval_score_repository.record = AsyncMock(
        side_effect=[
            _fake_eval_score(metric_name="citation_validity", score=1.0, reason="ok"),
            _fake_eval_score(metric_name="web_search_invoked", score=1.0, reason=""),
            _fake_eval_score(metric_name="web_search_success", score=1.0, reason=""),
        ]
    )

    with patch("app.ai.runtime.generation.online_scoring.job.sync_eval_score") as sync_mock:
        await harness.job.run_once()

    synced_metrics = {call.kwargs["metric_name"] for call in sync_mock.call_args_list}
    assert "web_search_invoked" in synced_metrics
    assert "web_search_success" in synced_metrics


# ==============================================================
# E23 follow-up: Deep Research web-search invocation/success signal
# ==============================================================


def _deep_research_row(
    *, owner_id: uuid.UUID, generation_id: uuid.UUID, run_id: uuid.UUID
) -> GenerationUsage:
    return _make_usage_row(
        owner_id=owner_id,
        generation_id=generation_id,
        surface="deep_research",
        session_id=run_id,
    )


def _research_run(
    *,
    run_id: uuid.UUID,
    owner_id: uuid.UUID,
    budget_usage: dict,
    completed_at: datetime | None = None,
) -> ResearchRun:
    return ResearchRun(
        id=run_id,
        owner_id=owner_id,
        graph_thread_id=str(uuid.uuid4()),
        status="completed",
        completed_at=completed_at if completed_at is not None else datetime.now(UTC),
        budget_usage=budget_usage,
    )


@pytest.mark.asyncio
async def test_deep_research_web_search_signal_is_recorded_from_budget_usage() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _deep_research_row(owner_id=owner_id, generation_id=generation_id, run_id=run_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run = _research_run(
        run_id=run_id,
        owner_id=owner_id,
        budget_usage={"web_search_invoked": True, "web_search_success": True},
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=run)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["web_search_invoked"]["passed"] is True
    assert calls["web_search_success"]["passed"] is True


@pytest.mark.asyncio
async def test_deep_research_web_search_signal_omits_success_when_not_invoked() -> None:
    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _deep_research_row(owner_id=owner_id, generation_id=generation_id, run_id=run_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run = _research_run(
        run_id=run_id, owner_id=owner_id, budget_usage={"web_search_invoked": False}
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=run)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert calls["web_search_invoked"]["passed"] is False
    assert "web_search_success" not in calls


@pytest.mark.asyncio
async def test_deep_research_web_search_signal_absent_from_budget_usage_records_nothing() -> None:
    """No web search key at all (run predates this feature, or web search
    was disabled for the run) -- must not fabricate a False row."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _deep_research_row(owner_id=owner_id, generation_id=generation_id, run_id=run_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run = _research_run(run_id=run_id, owner_id=owner_id, budget_usage={"review_decision": "pass"})

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=run)

    await harness.job.run_once()

    metric_names = {c["metric_name"] for c in harness.record_calls()}
    assert metric_names.isdisjoint({"web_search_invoked", "web_search_success"})


@pytest.mark.asyncio
async def test_chat_row_never_looks_up_deep_research_web_search_signal() -> None:
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
async def test_deep_research_row_is_skipped_entirely_while_the_run_is_not_yet_terminal() -> None:
    """Regression test for a real bug found on a live Deep Research run
    (2026-08-12): the synthesis generation finishes well before the run
    itself reaches a terminal status (report approval, review, and the
    related-papers step all come after). Scoring the row early would
    still write `citation_validity` unconditionally, and
    `list_unscored_since()`'s anti-join treats *any* `ONLINE_SAMPLED` row
    as "already scored" forever -- so `web_search_invoked`/`_success`
    would never get a second chance once that happened. Confirmed live:
    `citation_validity` landed at 13:57:38 while the run didn't reach
    `completed_at` until 13:59:37, and the web-search signal was never
    written. The fix: skip the row entirely (write nothing) until the
    run is terminal, so it stays a legitimate candidate on the next
    poll."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _deep_research_row(owner_id=owner_id, generation_id=generation_id, run_id=run_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    in_progress_run = ResearchRun(
        id=run_id,
        owner_id=owner_id,
        graph_thread_id=str(uuid.uuid4()),
        status="researching",
        completed_at=None,
        budget_usage={},
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=in_progress_run)

    processed = await harness.job.run_once()

    assert processed == 1
    harness.eval_score_repository.record.assert_not_awaited()
    # Never even reads the artifact -- the terminal-status gate is
    # checked first, before anything else.
    harness.artifact_reader.read.assert_not_awaited()
    harness.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deep_research_row_is_scored_once_the_run_becomes_terminal() -> None:
    """The other half of the regression above -- once the run genuinely
    finishes, the row is no longer skipped and everything (citation
    check + web-search signal) is written together, atomically, in one
    pass."""

    owner_id = uuid.uuid4()
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()
    row = _deep_research_row(owner_id=owner_id, generation_id=generation_id, run_id=run_id)
    artifact = GenerationArtifactBuilder().build(
        result=_make_artifact_result(owner_id=owner_id, generation_id=generation_id)
    )
    run = _research_run(
        run_id=run_id,
        owner_id=owner_id,
        budget_usage={"web_search_invoked": True, "web_search_success": True},
    )

    harness = _JobHarness()
    harness.generation_usage_repository.list_unscored_since = AsyncMock(return_value=[row])
    harness.artifact_reader.read = AsyncMock(return_value=artifact)
    harness.research_run_repository.get_by_id_for_owner = AsyncMock(return_value=run)

    await harness.job.run_once()

    calls = {c["metric_name"]: c for c in harness.record_calls()}
    assert "citation_validity" in calls
    assert calls["web_search_invoked"]["passed"] is True
    assert calls["web_search_success"]["passed"] is True
