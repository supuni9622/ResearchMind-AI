"""
Research artifact models.

Wired into `ResearchService` (research_api_prd.md) as a best-effort,
write-only audit trail -- Postgres (`ResearchSession`) is the live read
path, per that PRD's design decision to follow this codebase's existing
Chat/Conversation precedent rather than its own "database as index"
phrasing. There is still no Research Runtime (planner/decomposition),
so `plan`/`queries` are always written empty; fields stay loosely typed
(`dict[str, Any]`) since no `ResearchPlan`-shaped type exists to derive
from yet.

Storage layout:

    artifacts/research/{research_id}/
        plan.json          -- always {} (no planning runtime yet)
        queries.json        -- always {} (no planning runtime yet)
        retrievals.json
        citations.json
        report.json          -- includes the answer text
        evaluation.json      -- optional, unused today
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
