import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.routing.enums import RoutingStrategy
from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
from app.models.generation_usage import GenerationUsage
from app.models.research import ResearchConversation
from app.models.research_run import ResearchRun
from app.models.user import User
from app.repositories.generation_usage import GenerationUsageRepository
from sqlalchemy import select


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _make_conversation(session, *, owner_id: uuid.UUID) -> uuid.UUID:
    conversation = ResearchConversation(owner_id=owner_id)
    session.add(conversation)
    await session.flush()
    return conversation.id


def _make_usage(
    *,
    owner_id: uuid.UUID,
    cost: float,
    tokens: int,
    conversation_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    completed_at: datetime | None = None,
    generation_id: uuid.UUID | None = None,
    langsmith_run_id: uuid.UUID | None = None,
) -> GenerationUsage:
    return GenerationUsage(
        request_id=uuid.uuid4(),
        generation_id=generation_id or uuid.uuid4(),
        langsmith_run_id=langsmith_run_id,
        owner_id=owner_id,
        conversation_id=conversation_id,
        session_id=session_id,
        provider="groq",
        model="test-model",
        prompt_tokens=tokens,
        completion_tokens=0,
        total_tokens=tokens,
        estimated_cost_usd=cost,
        **({"completed_at": completed_at} if completed_at is not None else {}),
    )


def _make_run(*, owner_id: uuid.UUID, conversation_id: uuid.UUID) -> ResearchRun:
    return ResearchRun(
        owner_id=owner_id,
        conversation_id=conversation_id,
        graph_thread_id=str(uuid.uuid4()),
        status="completed",
    )


@pytest.mark.asyncio
async def test_record_persists_the_config_fingerprint(db_session) -> None:
    """
    EVALUATION_IMPLEMENTATION_TRACKER.md E8: `GenerationRequest`'s
    surface/prompt_version/chunking_strategy/embedding_model/reranker
    fields, plus `GenerationResult.statistics.routing_strategy`, must
    survive `record()` into `GenerationUsage` so a production answer can
    be traced back to the config that produced it. Exercised against a
    real Postgres row, not a mock.

    `request.routing_strategy` is deliberately left `None` here (the
    realistic case -- real callers essentially never override it) while
    `statistics.routing_strategy` is `AUTO`, mirroring exactly what
    `GenerationService._generate_with_routing()`/`StreamingService.
    stream_generate()` set post-hoc once routing has actually resolved a
    model. This is a real-bug regression test: `record()` used to read
    `request.routing_strategy` directly, which persisted `NULL` for
    every real production request since none of them set an explicit
    override -- see `docs/EVALUATION_IMPLEMENTATION_TRACKER.md` E8's
    "Update" note.
    """

    owner_id = await _make_owner(db_session)

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="What is RAG?",
        owner_id=owner_id,
        surface="chat",
        prompt_version="chat-v1",
        chunking_strategy="markdown",
        embedding_model="voyage-3-lite",
        reranker="voyage_ai",
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="test-model",
            routing_strategy=RoutingStrategy.AUTO,
        ),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="RAG is retrieval-augmented generation.",
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.surface == "chat"
    assert row.prompt_version == "chat-v1"
    assert row.chunking_strategy == "markdown"
    assert row.embedding_model == "voyage-3-lite"
    assert row.reranker == "voyage_ai"
    assert row.routing_strategy == "auto"


@pytest.mark.asyncio
async def test_record_leaves_the_config_fingerprint_null_for_internal_calls(db_session) -> None:
    """Internal helper generations (planning, review, memory extraction, ...)
    never populate the fingerprint fields -- `record()` must not require
    them, and they should persist as NULL rather than an empty string or
    a crash."""

    owner_id = await _make_owner(db_session)

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="Summarize this turn for memory extraction.",
        owner_id=owner_id,
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="...",
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.surface is None
    assert row.prompt_version is None
    assert row.routing_strategy is None


@pytest.mark.asyncio
async def test_sum_for_conversation_includes_deep_research_run_usage(db_session) -> None:
    """Deep Research generation calls tag `session_id=research_run.id`, not
    `conversation_id` (see `ResearchPlanner.plan`) -- a conversation with
    only a Deep Research run must still surface its cost, not $0."""

    owner_id = await _make_owner(db_session)
    conversation_id = await _make_conversation(db_session, owner_id=owner_id)

    run = _make_run(owner_id=owner_id, conversation_id=conversation_id)
    db_session.add(run)
    await db_session.flush()

    db_session.add(_make_usage(owner_id=owner_id, cost=1.5, tokens=100, session_id=run.id))
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    summary = await repository.sum_for_conversation(conversation_id, owner_id)

    assert summary["total_cost_usd"] == pytest.approx(1.5)
    assert summary["total_requests"] == 1
    assert summary["total_tokens"] == 100


@pytest.mark.asyncio
async def test_sum_for_conversation_combines_linear_and_deep_research_usage(db_session) -> None:
    owner_id = await _make_owner(db_session)
    conversation_id = await _make_conversation(db_session, owner_id=owner_id)

    run = _make_run(owner_id=owner_id, conversation_id=conversation_id)
    db_session.add(run)
    await db_session.flush()

    db_session.add_all(
        [
            _make_usage(owner_id=owner_id, cost=0.25, tokens=50, conversation_id=conversation_id),
            _make_usage(owner_id=owner_id, cost=2.0, tokens=400, session_id=run.id),
        ]
    )
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    summary = await repository.sum_for_conversation(conversation_id, owner_id)

    assert summary["total_cost_usd"] == pytest.approx(2.25)
    assert summary["total_requests"] == 2
    assert summary["total_tokens"] == 450


@pytest.mark.asyncio
async def test_sum_for_conversation_excludes_other_owners_run_usage(db_session) -> None:
    owner_id = await _make_owner(db_session)
    other_owner_id = await _make_owner(db_session)
    conversation_id = await _make_conversation(db_session, owner_id=owner_id)

    run = _make_run(owner_id=other_owner_id, conversation_id=conversation_id)
    db_session.add(run)
    await db_session.flush()

    db_session.add(_make_usage(owner_id=other_owner_id, cost=9.0, tokens=900, session_id=run.id))
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    summary = await repository.sum_for_conversation(conversation_id, owner_id)

    assert summary["total_cost_usd"] == pytest.approx(0.0)
    assert summary["total_requests"] == 0
    assert summary["total_tokens"] == 0


@pytest.mark.asyncio
async def test_daily_cost_totals_groups_and_sums_by_calendar_day(db_session) -> None:
    """E18: real date-grouping against Postgres, not a mock -- two rows on
    the same day must collapse into one total, and rows from different
    owners must both count (system-wide, unlike summary_for_owner)."""

    owner_a = await _make_owner(db_session)
    owner_b = await _make_owner(db_session)

    day_one = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)
    day_one_later = datetime(2026, 1, 5, 22, 30, tzinfo=UTC)
    day_two = datetime(2026, 1, 6, 10, 0, tzinfo=UTC)

    db_session.add_all(
        [
            _make_usage(owner_id=owner_a, cost=1.0, tokens=10, completed_at=day_one),
            _make_usage(owner_id=owner_b, cost=2.5, tokens=20, completed_at=day_one_later),
            _make_usage(owner_id=owner_a, cost=3.0, tokens=30, completed_at=day_two),
        ]
    )
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    totals = await repository.daily_cost_totals(since=datetime(2026, 1, 1, tzinfo=UTC))

    by_day = {day: cost for day, cost in totals}
    assert by_day[date(2026, 1, 5)] == pytest.approx(3.5)
    assert by_day[date(2026, 1, 6)] == pytest.approx(3.0)


@pytest.mark.asyncio
async def test_daily_cost_totals_excludes_rows_before_since(db_session) -> None:
    owner_id = await _make_owner(db_session)

    db_session.add_all(
        [
            _make_usage(
                owner_id=owner_id,
                cost=5.0,
                tokens=50,
                completed_at=datetime(2025, 12, 31, tzinfo=UTC),
            ),
            _make_usage(
                owner_id=owner_id,
                cost=1.0,
                tokens=10,
                completed_at=datetime(2026, 1, 2, tzinfo=UTC),
            ),
        ]
    )
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    totals = await repository.daily_cost_totals(since=datetime(2026, 1, 1, tzinfo=UTC))

    assert [day for day, _ in totals] == [date(2026, 1, 2)]


@pytest.mark.asyncio
async def test_record_persists_langsmith_run_id(db_session) -> None:
    """E21's LangSmith-feedback follow-up: `GenerationResult.langsmith_run_id`
    (set post-hoc from `TraceHandle.run_id` once a trace has actually run,
    same pattern as `statistics.routing_strategy`) must survive `record()`
    so `FeedbackService` can look it up later by `generation_id`."""

    owner_id = await _make_owner(db_session)
    run_id = uuid.uuid4()

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="What is RAG?",
        owner_id=owner_id,
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="RAG is retrieval-augmented generation.",
        langsmith_run_id=run_id,
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.langsmith_run_id == run_id


@pytest.mark.asyncio
async def test_record_leaves_langsmith_run_id_null_when_tracing_not_configured(db_session) -> None:
    owner_id = await _make_owner(db_session)

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="What is RAG?",
        owner_id=owner_id,
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="RAG is retrieval-augmented generation.",
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.langsmith_run_id is None


@pytest.mark.asyncio
async def test_get_langsmith_run_id_returns_the_stored_run_id(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()
    run_id = uuid.uuid4()

    db_session.add(
        _make_usage(
            owner_id=owner_id,
            cost=1.0,
            tokens=10,
            generation_id=generation_id,
            langsmith_run_id=run_id,
        )
    )
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    result = await repository.get_langsmith_run_id(generation_id)

    assert result == run_id


@pytest.mark.asyncio
async def test_get_langsmith_run_id_returns_none_for_unknown_generation(db_session) -> None:
    repository = GenerationUsageRepository(db_session)

    result = await repository.get_langsmith_run_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_record_persists_guardrail_final_action(db_session) -> None:
    """E5: `GenerationResult.guardrails.final_action` must survive
    `record()` -- it's the free "guardrail-flagged" signal
    `OnlineScoringJob`'s sampling decision reads directly off the
    persisted row, per EVALUATION_PLAN.md §14."""

    owner_id = await _make_owner(db_session)

    stage_result = GuardrailResult(
        stage=GuardrailStage.GENERATION, passed=True, blocked=False, action=GuardrailAction.WARN
    )
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="What is RAG?",
        owner_id=owner_id,
        surface="chat",
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="RAG is retrieval-augmented generation.",
        guardrails=GuardrailReport(
            input_result=stage_result,
            retrieval_result=stage_result,
            generation_result=stage_result,
            final_action=GuardrailAction.WARN,
            blocked=False,
        ),
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.guardrail_final_action == "warn"


@pytest.mark.asyncio
async def test_record_leaves_guardrail_final_action_null_when_guardrails_did_not_run(
    db_session,
) -> None:
    owner_id = await _make_owner(db_session)

    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="What is RAG?",
        owner_id=owner_id,
    )
    result = GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=GenerationProvider.GROQ, model="test-model"),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="RAG is retrieval-augmented generation.",
    )

    repository = GenerationUsageRepository(db_session)
    await repository.record(result)
    await db_session.flush()

    row = (
        await db_session.execute(
            select(GenerationUsage).where(GenerationUsage.request_id == request.request_id)
        )
    ).scalar_one()

    assert row.guardrail_final_action is None


@pytest.mark.asyncio
async def test_list_unscored_since_returns_answer_producing_rows_without_a_score(
    db_session,
) -> None:
    owner_id = await _make_owner(db_session)
    now = datetime.now(UTC)

    scored = _make_usage(owner_id=owner_id, cost=1.0, tokens=10, completed_at=now)
    scored.surface = "chat"
    unscored = _make_usage(owner_id=owner_id, cost=1.0, tokens=10, completed_at=now)
    unscored.surface = "chat"
    internal = _make_usage(owner_id=owner_id, cost=1.0, tokens=10, completed_at=now)
    internal.surface = None
    db_session.add_all([scored, unscored, internal])
    await db_session.flush()

    db_session.add(
        EvalScore(
            owner_id=owner_id,
            generation_id=scored.generation_id,
            metric_name="citation_validity",
            score=1.0,
            passed=True,
            reason="ok",
            source=EvalScoreSource.ONLINE_SAMPLED.value,
            sample_category="not_sampled",
        )
    )
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    candidates = await repository.list_unscored_since(
        since=now - timedelta(hours=1),
        limit=10,
    )

    candidate_ids = {row.generation_id for row in candidates}
    assert unscored.generation_id in candidate_ids
    assert scored.generation_id not in candidate_ids
    assert internal.generation_id not in candidate_ids


@pytest.mark.asyncio
async def test_list_unscored_since_excludes_rows_before_the_window(db_session) -> None:
    owner_id = await _make_owner(db_session)

    old_row = _make_usage(
        owner_id=owner_id,
        cost=1.0,
        tokens=10,
        completed_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    old_row.surface = "chat"
    db_session.add(old_row)
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    candidates = await repository.list_unscored_since(
        since=datetime(2026, 1, 1, tzinfo=UTC),
        limit=10,
    )

    assert old_row.generation_id not in {row.generation_id for row in candidates}


@pytest.mark.asyncio
async def test_list_unscored_since_respects_the_limit(db_session) -> None:
    owner_id = await _make_owner(db_session)
    now = datetime.now(UTC)

    rows = []
    for _ in range(3):
        row = _make_usage(owner_id=owner_id, cost=1.0, tokens=10, completed_at=now)
        row.surface = "chat"
        rows.append(row)
    db_session.add_all(rows)
    await db_session.flush()

    repository = GenerationUsageRepository(db_session)
    candidates = await repository.list_unscored_since(since=now - timedelta(hours=1), limit=2)

    assert len(candidates) == 2
