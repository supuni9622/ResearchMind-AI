"""
LangSmith-backed `MetricsRecorder` (AI Runtime Observability PRD §12).

PRD §12 keeps the existing `MetricsRecorder` abstraction and lists
`LangSmithMetricsRecorder` alongside `NoOpMetricsRecorder`/a future
Prometheus recorder as implementations -- this is that LangSmith one, not
a replacement for the interface or its default. `GenerationMetricsService`
still defaults to `NoOpMetricsRecorder`; this is an opt-in alternative,
constructed via `providers/langsmith/create.py`.
"""

from __future__ import annotations

import structlog

from app.ai.observability.providers.langsmith.client import get_langsmith_client
from app.ai.observability.providers.langsmith.tracing import current_run_id
from app.infrastructure.metrics.interfaces import MetricsRecorder

logger = structlog.get_logger()


class LangSmithMetricsRecorder(MetricsRecorder):
    """
    Feeds `record_duration`/`increment` calls to LangSmith as feedback on
    whichever trace is currently active (`tracing.py::current_run_id`).
    Best effort throughout: no active trace, no configured client, or an
    API failure are all logged and swallowed rather than raised (PRD §13
    Best Effort Recording) -- a metrics-recording hiccup must never fail
    the runtime execution it observes.
    """

    def record_duration(
        self,
        *,
        operation: str,
        duration_ms: float,
    ) -> None:
        self._send_feedback(key=f"{operation}_duration_ms", score=duration_ms)

    def increment(
        self,
        *,
        metric: str,
    ) -> None:
        self._send_feedback(key=metric, score=1)

    def _send_feedback(self, *, key: str, score: float) -> None:

        run_id = current_run_id.get()

        if run_id is None:
            logger.debug("observability.langsmith.feedback_skipped_no_run", key=key)
            return

        client = get_langsmith_client()

        if client is None:
            return

        try:
            client.create_feedback(run_id=run_id, key=key, score=score)
        except Exception:
            logger.warning(
                "observability.langsmith.feedback_failed",
                key=key,
                exc_info=True,
            )
