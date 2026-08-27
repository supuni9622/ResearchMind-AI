"""
Unit tests for sync_user_feedback (EVALUATION_IMPLEMENTATION_TRACKER.md
E21's LangSmith-feedback follow-up).

Covers:
- No-op when LangSmith isn't configured (get_langsmith_client returns None)
- Calls client.create_feedback with the expected key/score/feedback_id for
  both UP and DOWN ratings
- A create_feedback failure is swallowed, never raised
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.ai.observability.providers.langsmith import user_feedback as user_feedback_module
from app.ai.observability.providers.langsmith.user_feedback import sync_user_feedback
from app.models.enums import FeedbackRating

_RUN_ID = uuid.uuid4()
_FEEDBACK_ID = uuid.uuid4()


def test_noop_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(user_feedback_module, "get_langsmith_client", lambda: None)

    # Must not raise even though there's no client to call.
    sync_user_feedback(
        run_id=_RUN_ID,
        feedback_id=_FEEDBACK_ID,
        rating=FeedbackRating.UP,
        comment="great answer",
    )


def test_up_rating_sends_score_one(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(user_feedback_module, "get_langsmith_client", lambda: client)

    sync_user_feedback(
        run_id=_RUN_ID,
        feedback_id=_FEEDBACK_ID,
        rating=FeedbackRating.UP,
        comment="great answer",
    )

    client.create_feedback.assert_called_once_with(
        run_id=_RUN_ID,
        key="user_rating",
        score=1.0,
        comment="great answer",
        feedback_id=_FEEDBACK_ID,
    )


def test_down_rating_sends_score_zero(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(user_feedback_module, "get_langsmith_client", lambda: client)

    sync_user_feedback(
        run_id=_RUN_ID,
        feedback_id=_FEEDBACK_ID,
        rating=FeedbackRating.DOWN,
        comment=None,
    )

    client.create_feedback.assert_called_once_with(
        run_id=_RUN_ID,
        key="user_rating",
        score=0.0,
        comment=None,
        feedback_id=_FEEDBACK_ID,
    )


def test_create_feedback_failure_is_swallowed(monkeypatch) -> None:
    client = MagicMock()
    client.create_feedback.side_effect = RuntimeError("network down")
    monkeypatch.setattr(user_feedback_module, "get_langsmith_client", lambda: client)

    # Must not raise.
    sync_user_feedback(
        run_id=_RUN_ID,
        feedback_id=_FEEDBACK_ID,
        rating=FeedbackRating.UP,
        comment=None,
    )
