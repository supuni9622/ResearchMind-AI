"""
Unit tests for build_streaming_metrics_snapshot.

Covers:
- Fields pass through from StreamArtifact.metrics unchanged
- events_sent counts every event, not just tokens
- completed is True only when a COMPLETE event is present
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.ai.artifacts.streaming.models import (
    StreamArtifact,
    StreamArtifactMetadata,
    StreamMetrics,
    StreamTimelineEntry,
)
from app.ai.observability.metrics.streaming import build_streaming_metrics_snapshot
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider


def _event(event_type: str) -> StreamEvent:
    return StreamEvent(
        category=EventCategory.GENERATION,
        type=event_type,
        timestamp=datetime.now(UTC),
    )


def _make_artifact(*, events: list[StreamEvent], metrics: StreamMetrics) -> StreamArtifact:
    return StreamArtifact(
        metadata=StreamArtifactMetadata(
            stream_id=uuid.uuid4(),
            provider=GenerationProvider.GROQ,
            model="test-model",
        ),
        events=events,
        timeline=[StreamTimelineEntry(event="generation_started", timestamp=datetime.now(UTC))],
        metrics=metrics,
    )


async def test_fields_pass_through_from_stream_metrics() -> None:
    artifact = _make_artifact(
        events=[_event(CoreEventType.TOKEN.value)],
        metrics=StreamMetrics(
            first_token_latency_ms=12.0,
            stream_duration_ms=100.0,
            tokens_per_second=5.0,
            disconnect_count=2,
        ),
    )

    snapshot = build_streaming_metrics_snapshot(artifact)

    assert snapshot.stream_id == artifact.metadata.stream_id
    assert snapshot.provider == GenerationProvider.GROQ
    assert snapshot.model == "test-model"
    assert snapshot.ttft_ms == 12.0
    assert snapshot.stream_duration_ms == 100.0
    assert snapshot.tokens_per_second == 5.0
    assert snapshot.disconnects == 2


async def test_events_sent_counts_every_event() -> None:
    artifact = _make_artifact(
        events=[
            _event(CoreEventType.START.value),
            _event(CoreEventType.TOKEN.value),
            _event(CoreEventType.TOKEN.value),
            _event(CoreEventType.COMPLETE.value),
        ],
        metrics=StreamMetrics(stream_duration_ms=50.0),
    )

    snapshot = build_streaming_metrics_snapshot(artifact)

    assert snapshot.events_sent == 4


async def test_completed_true_only_when_complete_event_present() -> None:
    completed_artifact = _make_artifact(
        events=[_event(CoreEventType.TOKEN.value), _event(CoreEventType.COMPLETE.value)],
        metrics=StreamMetrics(stream_duration_ms=50.0),
    )
    incomplete_artifact = _make_artifact(
        events=[_event(CoreEventType.TOKEN.value)],
        metrics=StreamMetrics(stream_duration_ms=50.0),
    )

    assert build_streaming_metrics_snapshot(completed_artifact).completed is True
    assert build_streaming_metrics_snapshot(incomplete_artifact).completed is False
