"""
Unit tests for LangSmithMetricsRecorder.

Covers:
- record_duration/increment no-op when there's no active trace
  (current_run_id unset)
- Both call client.create_feedback with the expected key/score when a
  run is active
- A create_feedback failure is swallowed, never raised
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ai.observability.providers.langsmith import recorder as recorder_module
from app.ai.observability.providers.langsmith.recorder import LangSmithMetricsRecorder
from app.ai.observability.providers.langsmith.tracing import current_run_id


async def test_noop_when_no_active_run(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(recorder_module, "get_langsmith_client", lambda: client)
    recorder = LangSmithMetricsRecorder()

    recorder.increment(metric="generation_requests_total")
    recorder.record_duration(operation="generation", duration_ms=10.0)

    client.create_feedback.assert_not_called()


async def test_increment_sends_feedback_with_score_one(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(recorder_module, "get_langsmith_client", lambda: client)
    recorder = LangSmithMetricsRecorder()

    token = current_run_id.set("run-123")
    try:
        recorder.increment(metric="generation_requests_total")
    finally:
        current_run_id.reset(token)

    client.create_feedback.assert_called_once_with(
        run_id="run-123",
        key="generation_requests_total",
        score=1,
    )


async def test_record_duration_sends_feedback_with_duration_score(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(recorder_module, "get_langsmith_client", lambda: client)
    recorder = LangSmithMetricsRecorder()

    token = current_run_id.set("run-123")
    try:
        recorder.record_duration(operation="generation", duration_ms=42.0)
    finally:
        current_run_id.reset(token)

    client.create_feedback.assert_called_once_with(
        run_id="run-123",
        key="generation_duration_ms",
        score=42.0,
    )


async def test_feedback_failure_is_swallowed(monkeypatch) -> None:
    client = MagicMock()
    client.create_feedback.side_effect = RuntimeError("network down")
    monkeypatch.setattr(recorder_module, "get_langsmith_client", lambda: client)
    recorder = LangSmithMetricsRecorder()

    token = current_run_id.set("run-123")
    try:
        # Must not raise.
        recorder.increment(metric="generation_requests_total")
    finally:
        current_run_id.reset(token)
