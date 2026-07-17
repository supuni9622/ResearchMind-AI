"""
Streaming artifact models (PRD §14).

Storage layout:

    artifacts/streams/{stream_id}/
        events.json
        timeline.json
        stream.json     (= metadata)
        metrics.json
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.enums import GenerationProvider


class StreamArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    stream_id: UUID

    request_id: UUID | None = None

    provider: GenerationProvider

    model: str


class StreamTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str
    """One of "generation_started" | "first_token" | "completion" | "disconnect"."""

    timestamp: datetime


class StreamMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_token_latency_ms: float | None = None

    stream_duration_ms: float

    tokens_per_second: float | None = None

    disconnect_count: int = 0


class StreamEventsFile(BaseModel):
    """Container so `events.json` holds one JSON object, not a bare list."""

    model_config = ConfigDict(extra="forbid")

    events: list[StreamEvent]


class StreamTimelineFile(BaseModel):
    """Container so `timeline.json` holds one JSON object, not a bare list."""

    model_config = ConfigDict(extra="forbid")

    entries: list[StreamTimelineEntry]


class StreamArtifact(BaseModel):
    """
    Canonical persistence model representing one completed stream.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: StreamArtifactMetadata

    events: list[StreamEvent]

    timeline: list[StreamTimelineEntry]

    metrics: StreamMetrics
