"""
Unit tests for FeedbackService's LangSmith-feedback wiring
(EVALUATION_IMPLEMENTATION_TRACKER.md E21's LangSmith-feedback follow-up).

`FeedbackRepository`/`GenerationUsageRepository` are mocked at the
repository boundary (matching tests/unit/services/test_cost_forecast.py's
convention); `sync_user_feedback` itself is covered separately in
tests/unit/ai/observability/providers/langsmith/test_user_feedback.py, so
here we only assert it's called (or not) with the right arguments.

Covers:
- A generation with a known langsmith_run_id triggers sync_user_feedback
  with that run id, the feedback's own id, and the submitted rating/comment
- A generation with no langsmith_run_id (tracing wasn't configured, or the
  row predates the column) skips the LangSmith call entirely
- The primary feedback write (repository.upsert + commit) always happens
  regardless of LangSmith wiring
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.enums import FeedbackRating, FeedbackSurface
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
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return Feedback(**defaults)


async def test_submit_syncs_to_langsmith_when_run_id_is_known() -> None:
    feedback = _make_feedback()
    repository = MagicMock()
    repository.upsert = AsyncMock(return_value=feedback)
    generation_usage_repository = MagicMock()
    run_id = uuid.uuid4()
    generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=run_id)
    session = MagicMock()
    session.commit = AsyncMock()

    service = FeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_usage_repository,
    )

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
    generation_usage_repository.get_langsmith_run_id.assert_awaited_once_with(_GENERATION_ID)
    sync_mock.assert_called_once_with(
        run_id=run_id,
        feedback_id=feedback.id,
        rating=FeedbackRating.UP,
        comment="nice",
    )


async def test_submit_skips_langsmith_when_run_id_is_unknown() -> None:
    feedback = _make_feedback()
    repository = MagicMock()
    repository.upsert = AsyncMock(return_value=feedback)
    generation_usage_repository = MagicMock()
    generation_usage_repository.get_langsmith_run_id = AsyncMock(return_value=None)
    session = MagicMock()
    session.commit = AsyncMock()

    service = FeedbackService(
        session=session,
        repository=repository,
        generation_usage_repository=generation_usage_repository,
    )

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
