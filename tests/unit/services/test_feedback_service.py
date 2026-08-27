"""
Unit tests for FeedbackService's LangSmith-feedback wiring
(EVALUATION_IMPLEMENTATION_TRACKER.md E21's LangSmith-feedback follow-up)
and its eval_scores mirroring (E6, EVALUATION_PLAN.md §16 phase 7).

`FeedbackRepository`/`GenerationUsageRepository`/`EvalScoreRepository`
are mocked at the repository boundary (matching
tests/unit/services/test_cost_forecast.py's convention); `sync_user_feedback`
itself is covered separately in
tests/unit/ai/observability/providers/langsmith/test_user_feedback.py, so
here we only assert it's called (or not) with the right arguments.

Covers:
- A generation with a known langsmith_run_id triggers sync_user_feedback
  with that run id, the feedback's own id, and the submitted rating/comment
- A generation with no langsmith_run_id (tracing wasn't configured, or the
  row predates the column) skips the LangSmith call entirely
- The primary feedback write (repository.upsert + commit) always happens
  regardless of LangSmith wiring
- Every submission also upserts a mirrored `eval_scores` row
  (source=human_feedback, metric_name="user_rating"), with score/passed
  derived from the rating and reason falling back to a synthesized string
  when no comment was given
- Objective/preference classification (E11): only runs when there's a
  comment, and its result lands on both the feedback row and its
  eval_scores mirror
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.runtime.generation.comment_classification.models import (
    CommentClassificationDecision,
)
from app.models.enums import CommentClassification, EvalScoreSource, FeedbackRating, FeedbackSurface
from app.models.feedback import Feedback
from app.services.feedback import FeedbackService

_OWNER_ID = uuid.uuid4()
_GENERATION_ID = uuid.uuid4()


def _make_feedback(**overrides: object) -> Feedback:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "owner_id": _OWNER_ID,
        "generation_id": _GENERATION_ID,
        "surface": FeedbackSurface.CHAT.value,
        "rating": FeedbackRating.UP.value,
        "comment": None,
        "comment_classification": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Feedback(**defaults)


def _make_service(
    *,
    feedback: Feedback,
    langsmith_run_id: uuid.UUID | None,
    classification: CommentClassification = CommentClassification.OBJECTIVE,
) -> tuple[FeedbackService, MagicMock, MagicMock, MagicMock, MagicMock]:
    repository = MagicMock()
    repository.upsert = AsyncMock(return_value=feedback)
    generation_usage_repository = MagicMock()
    generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=langsmith_run_id)
    eval_score_repository = MagicMock()
    eval_score_repository.upsert = AsyncMock()
    session = MagicMock()
    session.commit = AsyncMock()
    comment_classification_service = MagicMock()
    comment_classification_service.classify = AsyncMock(
        return_value=CommentClassificationDecision(classification=classification, reason="r")
    )
    preference_memory_writer = MagicMock()
    preference_memory_writer.remember_feedback_preference = AsyncMock()

    service = FeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_usage_repository,
        eval_score_repository=eval_score_repository,
        comment_classification_service=comment_classification_service,
        preference_memory_writer=preference_memory_writer,
    )
    return (
        service,
        session,
        eval_score_repository,
        comment_classification_service,
        preference_memory_writer,
    )


async def test_submit_syncs_to_langsmith_when_run_id_is_known() -> None:
    feedback = _make_feedback()
    run_id = uuid.uuid4()
    service, session, _, _, _ = _make_service(feedback=feedback, langsmith_run_id=run_id)

    with patch("app.services.feedback.sync_user_feedback") as sync_mock:
        result = await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.UP,
            comment="nice",
        )

    assert result is feedback
    session.commit.assert_awaited_once()
    sync_mock.assert_called_once_with(
        run_id=run_id,
        feedback_id=feedback.id,
        rating=FeedbackRating.UP,
        comment="nice",
    )


async def test_submit_skips_langsmith_when_run_id_is_unknown() -> None:
    feedback = _make_feedback()
    service, session, _, _, _ = _make_service(feedback=feedback, langsmith_run_id=None)

    with patch("app.services.feedback.sync_user_feedback") as sync_mock:
        result = await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment=None,
        )

    assert result is feedback
    session.commit.assert_awaited_once()
    sync_mock.assert_not_called()


async def test_submit_mirrors_a_thumbs_up_into_eval_scores() -> None:
    feedback = _make_feedback()
    service, _, eval_score_repository, _, _ = _make_service(
        feedback=feedback, langsmith_run_id=None, classification=CommentClassification.OBJECTIVE
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.UP,
            comment="cited the right paper",
        )

    eval_score_repository.upsert.assert_awaited_once_with(
        owner_id=_OWNER_ID,
        generation_id=_GENERATION_ID,
        metric_name="user_rating",
        score=1.0,
        passed=True,
        reason="cited the right paper",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
        comment_classification="objective",
    )


async def test_submit_mirrors_a_thumbs_down_into_eval_scores() -> None:
    feedback = _make_feedback(rating=FeedbackRating.DOWN.value)
    service, _, eval_score_repository, _, _ = _make_service(
        feedback=feedback, langsmith_run_id=None
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment=None,
        )

    eval_score_repository.upsert.assert_awaited_once_with(
        owner_id=_OWNER_ID,
        generation_id=_GENERATION_ID,
        metric_name="user_rating",
        score=0.0,
        passed=False,
        reason="user rated down",
        source=EvalScoreSource.HUMAN_FEEDBACK.value,
        comment_classification=None,
    )


async def test_submit_classifies_the_comment_when_one_is_given() -> None:
    feedback = _make_feedback(comment="too formal", comment_classification="preference")
    service, _, eval_score_repository, classification_service, _ = _make_service(
        feedback=feedback,
        langsmith_run_id=None,
        classification=CommentClassification.PREFERENCE,
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment="too formal",
        )

    classification_service.classify.assert_awaited_once_with(
        comment="too formal",
        owner_id=_OWNER_ID,
        generation_id=_GENERATION_ID,
    )
    assert eval_score_repository.upsert.call_args.kwargs["comment_classification"] == "preference"


async def test_submit_skips_classification_when_there_is_no_comment() -> None:
    feedback = _make_feedback()
    service, _, _, classification_service, _ = _make_service(
        feedback=feedback, langsmith_run_id=None
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.UP,
            comment=None,
        )

    classification_service.classify.assert_not_awaited()


async def test_eval_score_mirror_commits_in_the_same_transaction_as_feedback() -> None:
    """The mirror must be upserted before `session.commit()`, not after --
    otherwise a crash between the two writes could leave feedback recorded
    with no matching eval_scores row."""

    feedback = _make_feedback()
    service, session, eval_score_repository, _, _ = _make_service(
        feedback=feedback, langsmith_run_id=None
    )

    call_order: list[str] = []
    eval_score_repository.upsert.side_effect = lambda **_: call_order.append("upsert")
    session.commit.side_effect = lambda: call_order.append("commit")

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.UP,
            comment=None,
        )

    assert call_order == ["upsert", "commit"]


async def test_submit_remembers_a_preference_comment_as_user_memory() -> None:
    feedback = _make_feedback(comment="too formal", comment_classification="preference")
    service, session, _, _, preference_memory_writer = _make_service(
        feedback=feedback, langsmith_run_id=None, classification=CommentClassification.PREFERENCE
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment="too formal, please be more casual",
        )

    preference_memory_writer.remember_feedback_preference.assert_awaited_once()
    kwargs = preference_memory_writer.remember_feedback_preference.await_args.kwargs
    assert kwargs["owner_id"] == _OWNER_ID
    assert kwargs["content"] == "too formal, please be more casual"
    assert kwargs["generation_id"] == _GENERATION_ID
    assert kwargs["surface"] == FeedbackSurface.CHAT
    assert session.commit.await_count == 1


async def test_feedback_commits_before_preference_memory_is_attempted() -> None:
    feedback = _make_feedback(comment="too formal", comment_classification="preference")
    service, session, _, _, preference_memory_writer = _make_service(
        feedback=feedback,
        langsmith_run_id=None,
        classification=CommentClassification.PREFERENCE,
    )
    call_order: list[str] = []
    session.commit.side_effect = lambda: call_order.append("feedback_commit")
    preference_memory_writer.remember_feedback_preference.side_effect = lambda **_: (
        call_order.append("memory_write")
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment="too formal",
        )

    assert call_order == ["feedback_commit", "memory_write"]


async def test_submit_does_not_remember_an_objective_comment() -> None:
    """Objective comments are facts about the answer's correctness, not the
    user -- they must never be written as a USER preference memory."""

    feedback = _make_feedback(comment="cited the wrong paper", comment_classification="objective")
    service, _, _, _, preference_memory_writer = _make_service(
        feedback=feedback, langsmith_run_id=None, classification=CommentClassification.OBJECTIVE
    )

    with patch("app.services.feedback.sync_user_feedback"):
        await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment="cited the wrong paper",
        )

    preference_memory_writer.remember_feedback_preference.assert_not_awaited()


async def test_submit_succeeds_even_when_the_preference_memory_write_fails() -> None:
    feedback = _make_feedback(comment="too formal", comment_classification="preference")
    service, session, _, _, preference_memory_writer = _make_service(
        feedback=feedback, langsmith_run_id=None, classification=CommentClassification.PREFERENCE
    )
    preference_memory_writer.remember_feedback_preference.side_effect = RuntimeError(
        "db unavailable"
    )

    with patch("app.services.feedback.sync_user_feedback"):
        result = await service.submit(
            owner_id=_OWNER_ID,
            generation_id=_GENERATION_ID,
            surface=FeedbackSurface.CHAT,
            rating=FeedbackRating.DOWN,
            comment="too formal",
        )

    assert result is feedback
    session.commit.assert_awaited_once()
