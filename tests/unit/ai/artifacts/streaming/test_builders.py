from __future__ import annotations

from datetime import timedelta

from app.ai.artifacts.streaming.builders import StreamArtifactBuilder
from app.ai.runtime.generation.enums import GenerationProvider

from tests.unit.ai.artifacts.streaming.conftest import make_events, utcnow


def test_build_derives_timeline_from_events() -> None:
    started_at = utcnow()
    events = make_events(started_at)
    completed_at = started_at + timedelta(milliseconds=150)

    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=events,
        started_at=started_at,
        completed_at=completed_at,
    )

    timeline_events = [entry.event for entry in artifact.timeline]
    assert timeline_events == ["generation_started", "first_token", "completion"]


def test_build_derives_metrics() -> None:
    started_at = utcnow()
    events = make_events(started_at)
    completed_at = started_at + timedelta(milliseconds=150)

    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=events,
        started_at=started_at,
        completed_at=completed_at,
    )

    assert artifact.metrics.stream_duration_ms == 150
    assert artifact.metrics.first_token_latency_ms == 50
    assert artifact.metrics.tokens_per_second is not None


def test_build_handles_no_token_events() -> None:
    started_at = utcnow()
    completed_at = started_at + timedelta(milliseconds=10)

    artifact = StreamArtifactBuilder().build(
        provider=GenerationProvider.GROQ,
        model="llama-3.3-70b",
        events=[],
        started_at=started_at,
        completed_at=completed_at,
    )

    assert artifact.metrics.first_token_latency_ms is None
    assert artifact.metrics.tokens_per_second is None
    assert [entry.event for entry in artifact.timeline] == ["generation_started", "completion"]
