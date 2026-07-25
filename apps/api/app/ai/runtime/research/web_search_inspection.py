"""Read-only access to a paused run's pending web-search suggestion.

While a run sits at `AWAITING_WEB_SEARCH_APPROVAL`, `evaluate_web_search_need`
has already written a `web_search_suggestion` into checkpointed state. This
module lets the API read that checkpoint directly, mirroring
`ResearchPlanInspectionService`.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.ai.runtime.research.checkpointing import postgres_checkpointer
from app.models.research_run import ResearchRun


class PendingWebSearchUnavailableError(RuntimeError):
    """Raised when a run has no web-search suggestion checkpointed yet (e.g.
    it isn't actually paused at the web-search-approval interrupt)."""


@dataclass(frozen=True)
class PendingWebSearchSnapshot:
    research_run_id: str
    suggested_query: str
    reason: str
    gap_question: str | None


class ResearchWebSearchInspectionService:
    def __init__(self, *, database_url: str) -> None:
        self._database_url = database_url

    async def get_pending_suggestion(self, run: ResearchRun) -> PendingWebSearchSnapshot:
        async with postgres_checkpointer(self._database_url) as checkpointer:
            checkpoint_tuple = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": run.graph_thread_id}}
            )
        if checkpoint_tuple is None:
            raise PendingWebSearchUnavailableError(
                f"Research run '{run.id}' has no checkpointed graph state."
            )
        values = checkpoint_tuple.checkpoint.get("channel_values", {})
        suggestion = values.get("web_search_suggestion")
        if not isinstance(suggestion, dict) or not suggestion.get("query"):
            raise PendingWebSearchUnavailableError(
                f"Research run '{run.id}' has no web-search suggestion awaiting review."
            )
        return PendingWebSearchSnapshot(
            research_run_id=str(run.id),
            suggested_query=str(suggestion["query"]),
            reason=str(suggestion.get("reason") or ""),
            gap_question=(
                str(suggestion["gap_question"]) if suggestion.get("gap_question") else None
            ),
        )
