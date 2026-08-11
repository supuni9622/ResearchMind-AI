"""
Integration tests for `FeedbackRepository` against a real Postgres row.

Closes the gap flagged in `EVALUATION_IMPLEMENTATION_TRACKER.md` E3: the
API-level tests (`tests/api/test_feedback.py`) use a fake service double
and never exercise the real `insert().on_conflict_do_update().returning()`
statement. These do.
"""

from __future__ import annotations

import uuid

import pytest
from app.models.enums import FeedbackRating, FeedbackSurface
from app.models.user import User
from app.repositories.feedback import FeedbackRepository


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
async def test_upsert_inserts_a_new_feedback_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    feedback = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment="cited the wrong paper",
    )

    assert feedback.owner_id == owner_id
    assert feedback.generation_id == generation_id
    assert feedback.surface == "chat"
    assert feedback.rating == "down"
    assert feedback.comment == "cited the wrong paper"


@pytest.mark.asyncio
async def test_upsert_updates_the_existing_row_on_conflict(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    first = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment="wrong citation",
    )
    second = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.UP,
        comment=None,
    )

    assert first.id == second.id
    assert second.rating == "up"
    assert second.comment is None


@pytest.mark.asyncio
async def test_upsert_is_isolated_per_owner(db_session) -> None:
    owner_1 = await _make_owner(db_session)
    owner_2 = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    first = await repository.upsert(
        owner_id=owner_1,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment=None,
    )
    second = await repository.upsert(
        owner_id=owner_2,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.UP,
        comment=None,
    )

    assert first.id != second.id


@pytest.mark.asyncio
async def test_get_for_generation_returns_none_when_no_feedback_exists(db_session) -> None:
    owner_id = await _make_owner(db_session)

    repository = FeedbackRepository(db_session)
    feedback = await repository.get_for_generation(owner_id=owner_id, generation_id=uuid.uuid4())

    assert feedback is None


@pytest.mark.asyncio
async def test_get_for_generation_returns_the_upserted_row(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.DEEP_RESEARCH,
        rating=FeedbackRating.UP,
        comment="great report",
    )

    feedback = await repository.get_for_generation(owner_id=owner_id, generation_id=generation_id)

    assert feedback is not None
    assert feedback.surface == "deep_research"
    assert feedback.comment == "great report"


@pytest.mark.asyncio
async def test_upsert_persists_comment_classification(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    feedback = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment="this cited the wrong paper",
        comment_classification="objective",
    )

    assert feedback.comment_classification == "objective"


@pytest.mark.asyncio
async def test_upsert_updates_comment_classification_on_a_resubmission(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = FeedbackRepository(db_session)
    await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment="too formal",
        comment_classification="preference",
    )
    updated = await repository.upsert(
        owner_id=owner_id,
        generation_id=generation_id,
        surface=FeedbackSurface.CHAT,
        rating=FeedbackRating.DOWN,
        comment="also cites the wrong paper",
        comment_classification="objective",
    )

    assert updated.comment_classification == "objective"
