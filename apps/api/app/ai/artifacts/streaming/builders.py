"""
Streaming artifact builder. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from app.ai.artifacts.streaming.models import (
    StreamArtifact,
    StreamArtifactMetadata,
    StreamMetrics,
    StreamTimelineEntry,
)
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider


class StreamArtifactBuilder:
    """
    Builds the canonical StreamArtifact from the events accumulated over
    one `StreamingService._stream_live()` call.
    """

    def build(
        self,
        *,
        provider: GenerationProvider,
        model: str,
        events: list[StreamEvent],
        started_at: datetime,
        completed_at: datetime,
        request_id: UUID | None = None,
        owner_id: UUID | None = None,
        session_id: UUID | None = None,
    ) -> StreamArtifact:

        timeline = self._build_timeline(
            events=events,
            started_at=started_at,
            completed_at=completed_at,
        )

        metrics = self._build_metrics(
            events=events,
            started_at=started_at,
            completed_at=completed_at,
        )

        return StreamArtifact(
            metadata=StreamArtifactMetadata(
                stream_id=uuid4(),
                owner_id=owner_id,
                session_id=session_id,
                request_id=request_id,
                provider=provider,
                model=model,
            ),
            events=events,
            timeline=timeline,
            metrics=metrics,
        )

    @staticmethod
    def _build_timeline(
        *,
        events: list[StreamEvent],
        started_at: datetime,
        completed_at: datetime,
    ) -> list[StreamTimelineEntry]:

        timeline = [
            StreamTimelineEntry(event="generation_started", timestamp=started_at),
        ]

        first_token = next(
            (event for event in events if event.type == CoreEventType.TOKEN.value),
            None,
        )
        if first_token is not None:
            timeline.append(
                StreamTimelineEntry(event="first_token", timestamp=first_token.timestamp),
            )

        timeline.append(
            StreamTimelineEntry(event="completion", timestamp=completed_at),
        )

        return timeline

    @staticmethod
    def _build_metrics(
        *,
        events: list[StreamEvent],
        started_at: datetime,
        completed_at: datetime,
    ) -> StreamMetrics:

        duration_ms = (completed_at - started_at).total_seconds() * 1000

        token_events = [event for event in events if event.type == CoreEventType.TOKEN.value]

        first_token_latency_ms: float | None = None
        if token_events:
            first_token_latency_ms = (token_events[0].timestamp - started_at).total_seconds() * 1000

        #
        # Character-count approximation, not a real token rate -- provider
        # `stream()` implementations only yield content deltas today, no
        # token usage (same documented gap as `StreamingService.
        # _store_completed_stream`'s estimated cache statistics).
        #
        total_chars = sum(len(event.content or "") for event in token_events)

        tokens_per_second: float | None = None
        if duration_ms > 0 and total_chars > 0:
            tokens_per_second = total_chars / (duration_ms / 1000)

        return StreamMetrics(
            first_token_latency_ms=first_token_latency_ms,
            stream_duration_ms=duration_ms,
            tokens_per_second=tokens_per_second,
            disconnect_count=0,
        )
