"""
Unit tests for NoOpTracer / LangSmithTracer.

Covers:
- NoOpTracer.trace() brackets nothing and lets exceptions propagate
- LangSmithTracer.trace() no-ops when no client is configured
- LangSmithTracer.trace() creates a run, sets current_run_id for the
  duration of the block, and clears it afterward
- LangSmithTracer.trace() calls update_run with error=None on success and
  error=str(exc) on failure, re-raising the original exception either way
- A create_run failure degrades to a plain no-op instead of raising
- `inputs` is passed through to create_run as the actual LangSmith Input
  panel content, while `tags` land under extra.metadata (plus ls_provider/
  ls_model_name for LangSmith's own cost calculation), not as `inputs`
- The yielded TraceHandle's set_output() populates update_run's `outputs`
  with content and a LangChain-style usage_metadata block
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.ai.observability.providers.langsmith import tracing as tracing_module
from app.ai.observability.providers.langsmith.tracing import (
    LangSmithTracer,
    NoOpTracer,
    current_run_id,
)


async def test_noop_tracer_brackets_nothing() -> None:
    tracer = NoOpTracer()

    with tracer.trace(name="generation", tags={"provider": "groq"}):
        pass


async def test_noop_tracer_lets_exceptions_propagate() -> None:
    tracer = NoOpTracer()

    with pytest.raises(ValueError), tracer.trace(name="generation"):
        raise ValueError("boom")


async def test_langsmith_tracer_noop_when_no_client(monkeypatch) -> None:
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: None)
    tracer = LangSmithTracer()

    with tracer.trace(name="generation"):
        assert current_run_id.get() is None


async def test_langsmith_tracer_sets_and_clears_run_id_on_success(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    assert current_run_id.get() is None

    with tracer.trace(name="generation", tags={"provider": "groq"}):
        assert current_run_id.get() is not None

    assert current_run_id.get() is None
    client.create_run.assert_called_once()
    client.update_run.assert_called_once()
    assert client.update_run.call_args.kwargs["error"] is None


async def test_langsmith_tracer_records_error_and_reraises_on_failure(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    with pytest.raises(ValueError), tracer.trace(name="generation"):
        raise ValueError("boom")

    assert current_run_id.get() is None
    assert client.update_run.call_args.kwargs["error"] == "boom"


async def test_langsmith_tracer_degrades_to_noop_when_create_run_fails(monkeypatch) -> None:
    client = MagicMock()
    client.create_run.side_effect = RuntimeError("network down")
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    with tracer.trace(name="generation"):
        assert current_run_id.get() is None

    client.update_run.assert_not_called()


async def test_langsmith_tracer_passes_inputs_and_puts_tags_under_metadata(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    with tracer.trace(
        name="generation",
        inputs={"prompt": "hello"},
        tags={"provider": "claude", "model": "claude-sonnet-5"},
    ):
        pass

    create_kwargs = client.create_run.call_args.kwargs
    assert create_kwargs["inputs"] == {"prompt": "hello"}
    assert create_kwargs["extra"]["metadata"]["provider"] == "claude"
    assert create_kwargs["extra"]["metadata"]["ls_provider"] == "claude"
    assert create_kwargs["extra"]["metadata"]["ls_model_name"] == "claude-sonnet-5"


async def test_langsmith_tracer_set_output_populates_update_run_outputs(monkeypatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    with tracer.trace(name="generation") as handle:
        handle.set_output(
            content="hello world",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        )

    outputs = client.update_run.call_args.kwargs["outputs"]
    assert outputs["content"] == "hello world"
    assert outputs["usage_metadata"] == {
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


async def test_langsmith_tracer_update_run_outputs_none_when_set_output_never_called(
    monkeypatch,
) -> None:
    client = MagicMock()
    monkeypatch.setattr(tracing_module, "get_langsmith_client", lambda: client)
    tracer = LangSmithTracer()

    with tracer.trace(name="generation"):
        pass

    assert client.update_run.call_args.kwargs["outputs"] is None
