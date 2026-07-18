"""
Canonical Agent Metrics Platform (AI Runtime Observability PRD §5.5).

PRD-labeled "Future platform" outright. `app/ai/agents/` doesn't exist in
this codebase yet ([[artifact-platform]] confirms it's still an empty
directory), so there is no `AgentResult`-shaped source to derive a
snapshot from -- only the canonical shape is defined here, matching how
`app/ai/artifacts/agent/` models were seeded ahead of a real Agent
Runtime. No builder function is provided; add one alongside whatever
`AgentResult` the eventual Agent Runtime introduces.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentMetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_run_id: UUID

    agent_steps: int | None = None

    tool_calls: int | None = None

    iterations: int | None = None

    approval_cycles: int | None = None

    loop_count: int | None = None

    completion_rate: float | None = None
