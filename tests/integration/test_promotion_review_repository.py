"""
Integration tests for `PromotionReviewRepository` against real Postgres
rows (E10, EVALUATION_PLAN.md §3/§15).

Covers:
- Good candidates: thumbs-up feedback, excluding already-reviewed generations
- Failure candidates: thumbs-down+objective feedback merged with failed
  online-sampled eval_scores, deduplicated to one row per generation
- A preference-classified thumbs-down never appears as a failure candidate
- create()/list_confirmed_unsynced()/mark_synced() round-trip
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.models.enums import EvalScoreSource, FeedbackRating
from app.models.eval_score import EvalScore
from app.models.feedback import Feedback
from app.models.user import User
from app.repositories.promotion_review import PromotionReviewRepository


async def _make_owner(session) -> uuid.UUID:
    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email=f"{uuid.uuid4()}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _make_feedback(
    session,
    *,
    owner_id: uuid.UUID,
    rating: str,
    comment_classification: str | None = None,
    generation_id: uuid.UUID | None = None,
) -> Feedback:
    feedback = Feedback(
        owner_id=owner_id,
        generation_id=generation_id or uuid.uuid4(),
        surface="chat",
        rating=rating,
        comment="c",
        comment_classification=comment_classification,
    )
    session.add(feedback)
    await session.flush()
    return feedback


@pytest.mark.asyncio
async def test_list_good_candidates_returns_thumbs_up(db_session) -> None:
    owner_id = await _make_owner(db_session)
    await _make_feedback(db_session, owner_id=owner_id, rating=FeedbackRating.UP.value)
    await _make_feedback(db_session, owner_id=owner_id, rating=FeedbackRating.DOWN.value)

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_good_candidates(limit=10, offset=0)

    assert total == 1
    assert candidates[0].reason == "c"


@pytest.mark.asyncio
async def test_list_failure_candidates_includes_objective_thumbs_down(db_session) -> None:
    owner_id = await _make_owner(db_session)
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.DOWN.value,
        comment_classification="objective",
    )

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_failure_candidates(limit=10, offset=0)

    assert total == 1


@pytest.mark.asyncio
async def test_list_failure_candidates_excludes_preference_thumbs_down(db_session) -> None:
    owner_id = await _make_owner(db_session)
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.DOWN.value,
        comment_classification="preference",
    )

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_failure_candidates(limit=10, offset=0)

    assert total == 0


@pytest.mark.asyncio
async def test_list_preference_candidates_returns_preference_classified_thumbs_down(
    db_session,
) -> None:
    owner_id = await _make_owner(db_session)
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.DOWN.value,
        comment_classification="preference",
    )

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_preference_candidates(limit=10, offset=0)

    assert total == 1
    assert "classifier: preference" in candidates[0].reason


@pytest.mark.asyncio
async def test_list_preference_candidates_excludes_objective_thumbs_down(db_session) -> None:
    owner_id = await _make_owner(db_session)
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.DOWN.value,
        comment_classification="objective",
    )

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_preference_candidates(limit=10, offset=0)

    assert total == 0


@pytest.mark.asyncio
async def test_reviewed_preference_generation_does_not_reappear(db_session) -> None:
    owner_id = await _make_owner(db_session)
    reviewer_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.DOWN.value,
        comment_classification="preference",
        generation_id=generation_id,
    )

    repository = PromotionReviewRepository(db_session)
    await repository.create(
        source="human_feedback",
        direction="failure",
        owner_id=owner_id,
        generation_id=generation_id,
        status="rejected",
        reviewed_by=reviewer_id,
    )

    candidates, total = await repository.list_preference_candidates(limit=10, offset=0)
    assert total == 0


@pytest.mark.asyncio
async def test_list_failure_candidates_includes_failed_online_scores(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()
    score = EvalScore(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="faithfulness",
        score=0.2,
        passed=False,
        reason="not grounded",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
    )
    db_session.add(score)
    await db_session.flush()

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_failure_candidates(limit=10, offset=0)

    assert total == 1
    assert "faithfulness failed" in candidates[0].reason


@pytest.mark.asyncio
async def test_list_failure_candidates_dedupes_to_one_per_generation(db_session) -> None:
    """A generation that failed two metrics must appear once, not twice --
    the queue reviews the generation, not each metric separately."""

    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()
    now = datetime.now(UTC)
    older = EvalScore(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="faithfulness",
        score=0.2,
        passed=False,
        reason="not grounded",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        created_at=now - timedelta(minutes=5),
    )
    newer = EvalScore(
        owner_id=owner_id,
        generation_id=generation_id,
        metric_name="citation_validity",
        score=0.0,
        passed=False,
        reason="fabricated citation",
        source=EvalScoreSource.ONLINE_SAMPLED.value,
        created_at=now,
    )
    db_session.add_all([older, newer])
    await db_session.flush()

    repository = PromotionReviewRepository(db_session)
    candidates, total = await repository.list_failure_candidates(limit=10, offset=0)

    assert total == 1
    assert "citation_validity failed" in candidates[0].reason


@pytest.mark.asyncio
async def test_reviewed_generation_does_not_reappear(db_session) -> None:
    owner_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()
    reviewer_id = await _make_owner(db_session)
    await _make_feedback(
        db_session,
        owner_id=owner_id,
        rating=FeedbackRating.UP.value,
        generation_id=generation_id,
    )

    repository = PromotionReviewRepository(db_session)
    await repository.create(
        source="human_feedback",
        direction="good",
        owner_id=owner_id,
        generation_id=generation_id,
        status="rejected",
        reviewed_by=reviewer_id,
    )

    candidates, total = await repository.list_good_candidates(limit=10, offset=0)
    assert total == 0


@pytest.mark.asyncio
async def test_create_confirm_then_sync_round_trip(db_session) -> None:
    owner_id = await _make_owner(db_session)
    reviewer_id = await _make_owner(db_session)
    generation_id = uuid.uuid4()

    repository = PromotionReviewRepository(db_session)
    review = await repository.create(
        source="human_feedback",
        direction="good",
        owner_id=owner_id,
        generation_id=generation_id,
        status="confirmed",
        reviewed_by=reviewer_id,
        question="What is X?",
        reference_answer="X is a thing.",
        contexts=["X is described here."],
        reference_context_ids=["doc.pdf"],
        expected_citation_ids=["doc.pdf"],
        query_type="factual",
        difficulty="easy",
        workflow="chat",
    )

    unsynced = await repository.list_confirmed_unsynced()
    assert review.id in {row.id for row in unsynced}

    await repository.mark_synced(review.id)

    unsynced_after = await repository.list_confirmed_unsynced()
    assert review.id not in {row.id for row in unsynced_after}
