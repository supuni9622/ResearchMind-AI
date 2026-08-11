"""
Unit tests for sync_eval_score (E5 LangSmith-sync follow-up, extends
E22's sync_user_feedback pattern to automated scores).

Covers:
- No-op when LangSmith isn't configured (get_langsmith_client returns None)
- Calls client.create_feedback with the metric name as the key, and the
  score/reason/eval_score_id passed straight through
- A create_feedback failure is swallowed, never raised
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.ai.observability.providers.langsmith import eval_score_sync as eval_score_sync_module
from app.ai.observability.providers.langsmith.eval_score_sync import sync_eval_score

_RUN_ID = uuid.uuid4()
_EVAL_SCORE_ID = uuid.uuid4()


def test_noop_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(eval_score_sync_module, "get_langsmith_client", lambda: None)

    # Must not raise even though there's no client to call.
    sync_eval_score(
        run_id=_RUN_ID,
        eval_score_id=_EVAL_SCORE_ID,
        metric_name="citation_validity",
        score=1.0,
        reason="all citation checks passed",
    )


def test_sends_the_metric_name_as_the_feedback_key(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(eval_score_sync_module, "get_langsmith_client", lambda: client)

    sync_eval_score(
        run_id=_RUN_ID,
        eval_score_id=_EVAL_SCORE_ID,
        metric_name="faithfulness",
        score=0.87,
        reason="grounded in context",
    )

    client.create_feedback.assert_called_once_with(
        run_id=_RUN_ID,
        key="faithfulness",
        score=0.87,
        comment="grounded in context",
        feedback_id=_EVAL_SCORE_ID,
    )


def test_a_none_score_is_passed_through_rather_than_defaulted(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(eval_score_sync_module, "get_langsmith_client", lambda: client)

    sync_eval_score(
        run_id=_RUN_ID,
        eval_score_id=_EVAL_SCORE_ID,
        metric_name="answer_relevancy",
        score=None,
        reason=None,
    )

    client.create_feedback.assert_called_once_with(
        run_id=_RUN_ID,
        key="answer_relevancy",
        score=None,
        comment=None,
        feedback_id=_EVAL_SCORE_ID,
    )


def test_create_feedback_failure_is_swallowed(monkeypatch) -> None:
    client = MagicMock()
    client.create_feedback.side_effect = RuntimeError("network down")
    monkeypatch.setattr(eval_score_sync_module, "get_langsmith_client", lambda: client)

    # Must not raise.
    sync_eval_score(
        run_id=_RUN_ID,
        eval_score_id=_EVAL_SCORE_ID,
        metric_name="citation_validity",
        score=1.0,
        reason=None,
    )
