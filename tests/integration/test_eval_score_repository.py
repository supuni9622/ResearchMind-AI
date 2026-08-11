"""Integration tests for `EvalScoreRepository` against a real Postgres row (E5)."""

from __future__ import annotations

import uuid

import pytest
from app.models.enums import EvalScoreSource
from app.models.eval_score import EvalScore
from app.models.user import User
from app.repositories.eval_score import EvalScoreRepository
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


@pytest.mark.asyncio
async def test_record_inserts_a_score_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="all citation checks passed",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    row = (
        await db_session.execute(select(EvalScore).where(EvalScore.generation_id == generation_id))
    ).scalar_one()

    assert row.owner_id == owner_id
    assert row.metric_name == "citation_validity"
    assert row.score == pytest.approx(1.0)
    assert row.passed is True
    assert row.source == "online_sampled"
    assert row.sample_category == "baseline_sampled"


@pytest.mark.asyncio
async def test_record_allows_multiple_metrics_for_the_same_generation(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="ok",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="answer_relevancy",
        score=0.87,
        passed=True,
        reason="relevant",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert {row.metric_name for row in rows} == {"citation_validity", "answer_relevancy"}


@pytest.mark.asyncio
async def test_record_is_a_no_op_on_conflict_for_the_same_generation_metric_source(
    db_session,
) -> None:
    """Defensive backstop against a race between two concurrent job ticks
    (`EvalScoreRepository.record()`'s own docstring) -- a second `record()`
    call for the same `(generation_id, metric_name, source)` must not
    raise, and must not overwrite the first score."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=1.0,
        passed=True,
        reason="first",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    await repository.record(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=0.0,
        passed=False,
        reason="second, should be ignored",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        sample_category="baseline_sampled",
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert len(rows) == 1
    assert rows[0].reason == "first"
