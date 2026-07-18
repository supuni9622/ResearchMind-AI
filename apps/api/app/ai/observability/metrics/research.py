"""
Canonical Research Metrics Platform (AI Runtime Observability PRD §5.4).

PRD-labeled "Future runtime metrics for deep research" -- this codebase's
`ResearchService` (`app/ai/research/service.py`) is a direct compose of
Retrieval -> Context -> Generation Runtime with no planning/decomposition/
iteration loop yet ([[research-api-platform]]), so `sub_questions`,
`tool_calls`, `mcp_calls`, and `iterations` have no real value to derive
today. The canonical shape is defined now so a future Research Runtime
(planning/decomposition/multi-step, per that PRD's §19) can populate it
without another schema migration; every field is optional so persisting
this snapshot today (all-`None` beyond what `ResearchOutcome` carries)
never breaks readers of the schema later.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.research.models import ResearchOutcome


class ResearchMetricsSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_id: UUID

    planning_duration_ms: float | None = None

    research_duration_ms: float | None = None

    review_duration_ms: float | None = None

    sub_questions: int | None = None

    tool_calls: int | None = None

    mcp_calls: int | None = None

    iterations: int | None = None

    total_cost: float | None = None

    total_tokens: int | None = None


def build_research_metrics_snapshot(
    outcome: ResearchOutcome,
) -> ResearchMetricsSnapshot:
    """
    Pure derivation from a completed `ResearchOutcome`. `research_duration_ms`
    is the only field with a real value today -- everything else is
    reserved for when a Research Runtime exists to produce it.
    """

    return ResearchMetricsSnapshot(
        research_id=outcome.research_id,
        research_duration_ms=outcome.duration_ms,
    )
