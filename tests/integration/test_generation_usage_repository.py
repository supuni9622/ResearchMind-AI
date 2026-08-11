import uuid

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.routing.enums import RoutingStrategy
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
) -> GenerationUsage:
    return GenerationUsage(
        request_id=uuid.uuid4(),
        generation_id=uuid.uuid4(),
        owner_id=owner_id,
        conversation_id=conversation_id,
        session_id=session_id,
        provider="groq",
        model="test-model",
        prompt_tokens=tokens,
        completion_tokens=0,
        total_tokens=tokens,
        estimated_cost_usd=cost,
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
