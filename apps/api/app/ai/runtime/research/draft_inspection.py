"""Read-only access to a paused run's in-flight draft, before it is published.

While a run sits at `AWAITING_APPROVAL`, the synthesized draft only exists
inside the LangGraph Postgres checkpoint -- `persist_final_report` (the node
that would otherwise expose it as a durable artifact) hasn't run yet. This
module lets the API read that checkpoint state directly, so a reviewer can
see (and, via `record_report_decision`'s `edited_draft`, revise) the report
before deciding.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.runtime.research.checkpointing import postgres_checkpointer
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.review import ResearchReview
from app.ai.runtime.research.synthesis.models import ResearchDraft
from app.models.research_run import ResearchRun


class PendingDraftUnavailableError(RuntimeError):
    """Raised when a run has no draft checkpointed yet (e.g. it isn't
    actually paused at the report-approval interrupt)."""


@dataclass(frozen=True)
class PendingDraftSnapshot:
    draft: ResearchDraft
    evidence: ResearchEvidenceBundle
    review: ResearchReview


class ResearchDraftInspectionService:
    def __init__(self, *, database_url: str) -> None:
        self._database_url = database_url

    async def get_pending_draft(self, run: ResearchRun) -> PendingDraftSnapshot:
        async with postgres_checkpointer(self._database_url) as checkpointer:
            checkpoint_tuple = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": run.graph_thread_id}}
            )
        if checkpoint_tuple is None:
            raise PendingDraftUnavailableError(
                f"Research run '{run.id}' has no checkpointed graph state."
            )
        values = checkpoint_tuple.checkpoint.get("channel_values", {})
        if "draft" not in values or "evidence_bundle" not in values or "review" not in values:
            raise PendingDraftUnavailableError(
                f"Research run '{run.id}' has no draft awaiting review yet."
            )
        return PendingDraftSnapshot(
            draft=ResearchDraft.model_validate(values["draft"]),
            evidence=ResearchEvidenceBundle.model_validate(values["evidence_bundle"]),
            review=ResearchReview.model_validate(values["review"]),
        )
