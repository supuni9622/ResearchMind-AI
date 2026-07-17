"""
Research artifact models (PRD §17) -- scaffold-only.

No runtime emits or consumes this today: `runtime/research/{decomposition,
planner,workflows}/` are all empty directories, confirmed via repo
search -- there is no Research Runtime yet to produce a plan, run
queries, or generate a report. Built ahead of the API surface per this
codebase's established pattern (see e.g. `runtime/events/research/
models.py::ResearchEventType`, also reserved/unwired). Fields are left
loosely typed (`dict[str, Any]`) rather than over-specified, since no
`ResearchPlan`/`RetrievalResult`-shaped types exist yet for this to
derive from -- wire in and tighten types once the Research Runtime
itself is designed.

Storage layout (unwired):

    artifacts/research/{research_id}/
        plan.json
        queries.json
        retrievals.json
        citations.json
        report.json
        evaluation.json
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata


class ResearchArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    research_id: UUID


class ResearchArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: ResearchArtifactMetadata

    plan: dict[str, Any]

    queries: dict[str, Any]

    retrievals: dict[str, Any]

    citations: dict[str, Any]

    report: dict[str, Any]

    evaluation: dict[str, Any] | None = None
