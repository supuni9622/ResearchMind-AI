"""
Unit tests for get_trace_url (E10's promotion-review queue) -- the
first *read* this codebase does against LangSmith, everything before it
(E5/E11/E19/E22) only ever wrote.

Covers:
- None when LangSmith isn't configured (get_langsmith_client returns None)
- Calls client.read_run then client.get_run_url, returns the result
- Any failure (read_run, get_run_url, or the client itself) degrades to
  None, never raises
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.ai.observability.providers.langsmith import trace_link as trace_link_module
from app.ai.observability.providers.langsmith.trace_link import get_trace_url

_RUN_ID = uuid.uuid4()


def test_none_when_langsmith_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(trace_link_module, "get_langsmith_client", lambda: None)

    assert get_trace_url(_RUN_ID) is None


def test_returns_the_run_url(monkeypatch) -> None:
    client = MagicMock()
    fake_run = MagicMock()
    client.read_run.return_value = fake_run
    client.get_run_url.return_value = "https://smith.langchain.com/o/x/projects/p/y/r/z"
    monkeypatch.setattr(trace_link_module, "get_langsmith_client", lambda: client)

    url = get_trace_url(_RUN_ID)

    client.read_run.assert_called_once_with(_RUN_ID)
    client.get_run_url.assert_called_once_with(run=fake_run)
    assert url == "https://smith.langchain.com/o/x/projects/p/y/r/z"


def test_read_run_failure_degrades_to_none(monkeypatch) -> None:
    client = MagicMock()
    client.read_run.side_effect = RuntimeError("not found")
    monkeypatch.setattr(trace_link_module, "get_langsmith_client", lambda: client)

    assert get_trace_url(_RUN_ID) is None


def test_get_run_url_failure_degrades_to_none(monkeypatch) -> None:
    client = MagicMock()
    client.read_run.return_value = MagicMock()
    client.get_run_url.side_effect = RuntimeError("network down")
    monkeypatch.setattr(trace_link_module, "get_langsmith_client", lambda: client)

    assert get_trace_url(_RUN_ID) is None
