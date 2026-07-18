"""
Observability artifact models (AI Runtime Observability PRD §8).

Storage layout:

    observability/{execution_id}/
        metadata.json
        metrics.json
        statistics.json   (only when a StatisticsSnapshot was computed)
        report.md

Unlike the Generation/Streaming artifacts (one concrete snapshot type
each), an execution being observed here can be a generation, a retrieval,
a stream, or (eventually) a research/agent run -- each with its own
canonical snapshot model (`app/ai/observability/metrics/*.py`). Rather
than a union type per runtime, `metrics`/`statistics` are stored as
`dict[str, Any]` (mirrors the `JsonDictFile` pattern the Research/Agent
artifacts already use for the same "no single concrete type fits every
caller" reason) -- callers pass `snapshot.model_dump(mode="json")` in via
`ObservabilityArtifactBuilder.build()`, never a hand-built dict.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata


class ObservabilityArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    execution_id: UUID
    """The generation_id/retrieval_id/stream_id/... this artifact observes."""

    runtime: str
    """Which runtime produced the observed execution, e.g. "generation",
    "retrieval", "streaming". A plain string, not `ArtifactRuntime` --
    that enum tracks *caller* runtime (chat/research/agent/...), a
    different dimension from *which platform* emitted this snapshot."""


class ObservabilityArtifact(BaseModel):
    """
    Canonical persistence model for one observability record (PRD §8).
    """

    model_config = ConfigDict(extra="forbid")

    metadata: ObservabilityArtifactMetadata

    metrics: dict[str, Any]

    statistics: dict[str, Any] | None = None

    report: str
