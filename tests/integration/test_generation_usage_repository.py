import uuid

import pytest
from app.models.generation_usage import GenerationUsage
from app.models.research import ResearchConversation
from app.models.research_run import ResearchRun
from app.models.user import User
from app.repositories.generation_usage import GenerationUsageRepository


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
