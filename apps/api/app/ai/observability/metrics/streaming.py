"""
Canonical Streaming Metrics Platform (AI Runtime Observability PRD §5.3).

Pure derivation from an already-built `StreamArtifact` (`app/ai/
artifacts/streaming/models.py`) -- reuses its `StreamMetrics` rather than
re-timing anything, and adds the event-count/lifecycle fields the PRD
asks for that the artifact doesn't already carry.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.streaming.models import StreamArtifact
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.generation.enums import GenerationProvider


class StreamingMetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stream_id: UUID

    provider: GenerationProvider

    model: str

    ttft_ms: float | None = None

    stream_duration_ms: float

    tokens_per_second: float | None = None

    events_sent: int

    disconnects: int

    completed: bool

    cancelled: bool | None = None
    """
    `StreamingService` has no cancellation concept yet (no client-abort
    signal is threaded through `_stream_live()`) -- left `None` rather
    than guessed. See [[streaming-platform]] known gaps.
    """


def build_streaming_metrics_snapshot(
    artifact: StreamArtifact,
) -> StreamingMetricsSnapshot:
    """
    Pure derivation of a `StreamingMetricsSnapshot` from a completed
    `StreamArtifact`. No side effects, no recording.
    """

    completed = any(event.type == CoreEventType.COMPLETE.value for event in artifact.events)

    return StreamingMetricsSnapshot(
        stream_id=artifact.metadata.stream_id,
        provider=artifact.metadata.provider,
        model=artifact.metadata.model,
        ttft_ms=artifact.metrics.first_token_latency_ms,
        stream_duration_ms=artifact.metrics.stream_duration_ms,
        tokens_per_second=artifact.metrics.tokens_per_second,
        events_sent=len(artifact.events),
        disconnects=artifact.metrics.disconnect_count,
        completed=completed,
    )
