"""Read-only access to a paused run's in-flight plan and evidence, before synthesis runs.

While a run sits at `AWAITING_PLAN_APPROVAL`, retrieval has already completed
and been aggregated into evidence, but no draft exists yet -- `synthesize`
(the node that would produce one) hasn't run. This module lets the API read
that checkpoint state directly, so a reviewer can see the gathered evidence
and the plan's goal (and, via `record_plan_decision`'s `edited_goal`, revise
it) before the synthesis call is spent.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.runtime.research.checkpointing import postgres_checkpointer
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.planner.models import ResearchPlan
from app.models.research_run import ResearchRun


class PendingPlanUnavailableError(RuntimeError):
    """Raised when a run has no evidence checkpointed yet (e.g. it isn't
    actually paused at the plan-approval interrupt)."""


@dataclass(frozen=True)
class PendingPlanSnapshot:
    plan: ResearchPlan
    evidence: ResearchEvidenceBundle


class ResearchPlanInspectionService:
    def __init__(self, *, database_url: str) -> None:
        self._database_url = database_url

    async def get_pending_plan(self, run: ResearchRun) -> PendingPlanSnapshot:
        async with postgres_checkpointer(self._database_url) as checkpointer:
            checkpoint_tuple = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": run.graph_thread_id}}
            )
        if checkpoint_tuple is None:
            raise PendingPlanUnavailableError(
                f"Research run '{run.id}' has no checkpointed graph state."
            )
        values = checkpoint_tuple.checkpoint.get("channel_values", {})
        if "plan" not in values or "evidence_bundle" not in values:
            raise PendingPlanUnavailableError(
                f"Research run '{run.id}' has no evidence awaiting plan review yet."
            )
        return PendingPlanSnapshot(
            plan=ResearchPlan.model_validate(values["plan"]),
            evidence=ResearchEvidenceBundle.model_validate(values["evidence_bundle"]),
        )
