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


@pytest.mark.asyncio
async def test_upsert_inserts_a_new_score_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    score = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="great answer",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )

    assert score.owner_id == owner_id
    assert score.metric_name == "user_rating"
    assert score.score == pytest.approx(1.0)
    assert score.passed is True
    assert score.source == "human_feedback"
    assert score.sample_category is None


@pytest.mark.asyncio
async def test_upsert_updates_the_existing_row_on_conflict(db_session) -> None:
    """E6: a user changing their vote (thumbs down -> thumbs up) must
    update the same mirrored row, not accumulate a second one -- matches
    `FeedbackRepository.upsert()`'s own semantics exactly."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = EvalScoreRepository(db_session)
    first = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=0.0,
        passed=False,
        reason="wrong citation",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    second = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason=None,
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )

    assert first.id == second.id
    assert second.score == pytest.approx(1.0)
    assert second.passed is True
    assert second.reason is None

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_upsert_and_record_coexist_for_the_same_generation_under_different_sources(
    db_session,
) -> None:
    """A human-feedback mirror (`upsert`) and an online-scoring free check
    (`record`) for the *same* generation must both survive -- the unique
    constraint is scoped to `(generation_id, metric_name, source)`, and
    `metric_name` differs here (`user_rating` vs `citation_validity`), so
    this also covers the same-metric-different-source case implicitly via
    the constraint's third column."""

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
    await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="nice",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
    )
    await db_session.flush()

    statement = select(EvalScore).where(EvalScore.generation_id == generation_id)
    rows = (await db_session.execute(statement)).scalars().all()

    assert {(row.metric_name, row.source) for row in rows} == {
        ("citation_validity", "online_sampled"),
        ("user_rating", "human_feedback"),
    }


@pytest.mark.asyncio
async def test_record_offline_example_inserts_a_row_with_no_owner_or_generation(
    db_session,
) -> None:
    """E6: an offline-benchmark row scores a fixed golden-dataset example,
    not a live production generation -- owner_id/generation_id must both
    be persistable as NULL (the check constraint requires only that
    dataset_example_id is set instead)."""

    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="grounded in context",
    )
    await db_session.flush()

    row = (
        await db_session.execute(select(EvalScore).where(EvalScore.dataset_example_id == "a1"))
    ).scalar_one()

    assert row.owner_id is None
    assert row.generation_id is None
    assert row.metric_name == "faithfulness"
    assert row.score == pytest.approx(0.9)
    assert row.source == "offline_benchmark"
    assert row.sample_category is None


@pytest.mark.asyncio
async def test_record_offline_example_is_append_only_across_repeated_runs(db_session) -> None:
    """Unlike record()/upsert(), a second offline score for the same
    example+metric must produce a SECOND row, not overwrite the first --
    each benchmark run is a distinct trend data point for E9's future
    segment-analysis, not a replacement of the last one."""

    repository = EvalScoreRepository(db_session)
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.9,
        passed=True,
        reason="run 1",
    )
    await repository.record_offline_example(
        dataset_example_id="a1",
        metric_name="faithfulness",
        score=0.7,
        passed=True,
        reason="run 2 -- regressed slightly",
    )
    await db_session.flush()

    rows = (
        (await db_session.execute(select(EvalScore).where(EvalScore.dataset_example_id == "a1")))
        .scalars()
        .all()
    )

    assert len(rows) == 2
    assert {row.reason for row in rows} == {"run 1", "run 2 -- regressed slightly"}
