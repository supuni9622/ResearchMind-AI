"""
Session artifact models (PRD §16).

Reserved for a future Session Runtime. `GenerationRequest.session_id`
and `StreamEvent.session_id` already exist as fields, but nothing in
this codebase populates them today -- the only real conversation
boundary that exists is `Conversation` (see `conversation/models.py`,
which is live and wired). Built ahead of the API surface per this
codebase's established pattern (see e.g. `runtime/events/research/
models.py::ResearchEventType`); wire in once a real session concept
exists.

Storage layout (unwired):

    artifacts/sessions/{session_id}/
        session.json
        timeline.json
        statistics.json
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata


class SessionArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID


class SessionTimelineEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str

    timestamp: datetime


class SessionStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_count: int = 0

    total_duration_ms: float = 0


class SessionArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: SessionArtifactMetadata

    timeline: list[SessionTimelineEntry]

    statistics: SessionStatistics


class SessionTimelineFile(BaseModel):
    """Container so `timeline.json` holds one JSON object, not a bare list."""

    model_config = ConfigDict(extra="forbid")

    entries: list[SessionTimelineEntry]
