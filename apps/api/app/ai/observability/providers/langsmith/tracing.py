"""
Runtime tracing (AI Runtime Observability PRD §11.1).

LangSmith owns request traces/nested traces/run trees/span visualization;
ResearchMind's job is only to create the trace and attach runtime
metadata/tags -- never to rebuild tracing infrastructure. `RuntimeTracer`
is the interface `GenerationService` (and any future runtime) depends on;
`NoOpTracer` is the default (zero cost, zero behavior change) and
`LangSmithTracer` is the real implementation, constructed only when
`settings.langsmith_api_key` is set (see `client.py`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import structlog

from app.ai.observability.providers.langsmith.client import get_langsmith_client

logger = structlog.get_logger()

current_run_id: ContextVar[str | None] = ContextVar(
    "observability_langsmith_current_run_id",
    default=None,
)
"""
Holds the LangSmith run id of whichever `LangSmithTracer.trace()` block is
currently active, so `LangSmithMetricsRecorder` (recorder.py) can attach
feedback to it without the two collaborators needing a direct reference to
each other. `None` outside any trace, or whenever tracing isn't configured.
"""


class TraceHandle(ABC):
    """
    Yielded by `RuntimeTracer.trace()`. Lets the caller attach the actual
    result once it's known -- content and token usage -- before the trace
    closes, so a LangSmith run shows a real Output panel (not "No
    outputs") and has the token counts LangSmith needs to compute cost.
    Calling this is optional; a trace with no `set_output()` call just
    has no output recorded, same as before this existed.
    """

    @abstractmethod
    def set_output(
        self,
        *,
        content: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None: ...


class _NoOpTraceHandle(TraceHandle):
    def set_output(
        self,
        *,
        content: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None:
        return None


class RuntimeTracer(ABC):
    """Every runtime execution should create a trace (PRD §11.1). This is
    the seam a caller (e.g. `GenerationService`) depends on instead of a
    concrete tracer."""

    @abstractmethod
    def trace(
        self,
        *,
        name: str,
        inputs: dict[str, Any] | None = None,
        tags: dict[str, Any] | None = None,
    ) -> AbstractContextManager[TraceHandle]: ...


class NoOpTracer(RuntimeTracer):
    """
    Default tracer. Brackets nothing -- every caller that doesn't wire a
    real tracer runs exactly as if tracing didn't exist (same degrade-to-
    nothing shape as `NoOpMetricsRecorder`).
    """

    @contextmanager
    def trace(
        self,
        *,
        name: str,
        inputs: dict[str, Any] | None = None,
        tags: dict[str, Any] | None = None,
    ) -> Iterator[TraceHandle]:
        yield _NoOpTraceHandle()


class _LangSmithTraceHandle(TraceHandle):
    def __init__(self) -> None:
        self.outputs: dict[str, Any] = {}

    def set_output(
        self,
        *,
        content: str | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ) -> None:
        if content is not None:
            self.outputs["content"] = content

        if prompt_tokens is not None or completion_tokens is not None or total_tokens is not None:
            self.outputs["usage_metadata"] = {
                "input_tokens": prompt_tokens or 0,
                "output_tokens": completion_tokens or 0,
                "total_tokens": (
                    total_tokens
                    if total_tokens is not None
                    else (prompt_tokens or 0) + (completion_tokens or 0)
                ),
            }


class LangSmithTracer(RuntimeTracer):
    """
    Creates one LangSmith run per traced block. Best-effort throughout --
    a LangSmith API hiccup is logged and swallowed, never raised or
    allowed to affect the wrapped block's own exception, since tracing
    must never fail the runtime execution it observes (PRD §13).
    """

    def __init__(self, *, project_name: str | None = None) -> None:
        self._project_name = project_name

    @contextmanager
    def trace(
        self,
        *,
        name: str,
        inputs: dict[str, Any] | None = None,
        tags: dict[str, Any] | None = None,
    ) -> Iterator[TraceHandle]:

        client = get_langsmith_client()

        if client is None:
            yield _NoOpTraceHandle()
            return

        run_id = uuid4()

        #
        # LangSmith's Input/Output panels render whatever is passed as
        # `inputs`/`outputs` -- the caller's actual prompt, not the
        # provider/model/runtime tags. Those tags go under
        # `extra.metadata` instead (LangSmith's convention for run
        # metadata), duplicating `provider`/`model` as `ls_provider`/
        # `ls_model_name` -- the keys LangSmith's own cost calculator
        # looks for to price well-known models automatically.
        #
        try:
            client.create_run(
                name=name,
                inputs=inputs or {},
                run_type="llm",
                id=run_id,
                project_name=self._project_name,
                start_time=datetime.now(UTC),
                extra={
                    "metadata": {
                        **(tags or {}),
                        "ls_provider": (tags or {}).get("provider"),
                        "ls_model_name": (tags or {}).get("model"),
                    }
                },
            )
        except Exception:
            logger.warning("observability.langsmith.trace_start_failed", exc_info=True)
            yield _NoOpTraceHandle()
            return

        token = current_run_id.set(str(run_id))

        error: str | None = None
        handle = _LangSmithTraceHandle()

        try:
            yield handle
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            current_run_id.reset(token)

            try:
                client.update_run(
                    run_id,
                    end_time=datetime.now(UTC),
                    error=error,
                    outputs=handle.outputs or None,
                )
            except Exception:
                logger.warning("observability.langsmith.trace_end_failed", exc_info=True)
