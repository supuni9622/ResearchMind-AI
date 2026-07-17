"""
Agent artifact models (PRD §18) -- scaffold-only.

No runtime emits or consumes this today: `app/ai/agents/{evaluator,
planner,research,reviewer,shared,summarizer}/` are all empty
directories, confirmed via repo search -- there is no Agent Runtime
yet. PRD §18 itself frames Agent Artifacts as "Future Runtime
Foundation". Built ahead of the API surface per this codebase's
established pattern (see e.g. `runtime/events/agent/models.py::
AgentEventType`, also reserved/unwired). Fields are left loosely typed
(`dict[str, Any]`) for the same reason as `research/models.py`.

Storage layout (unwired):

    artifacts/agents/{run_id}/
        state.json
        tools.json
        execution_graph.json
        events.json
        memory.json
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.models import ArtifactMetadata


class AgentArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    run_id: UUID


class AgentArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metadata: AgentArtifactMetadata

    state: dict[str, Any]

    tools: dict[str, Any]

    execution_graph: dict[str, Any]

    events: dict[str, Any]

    memory: dict[str, Any]
