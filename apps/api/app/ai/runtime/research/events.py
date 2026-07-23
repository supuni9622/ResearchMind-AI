"""ResearchMind-owned event adaptation for LangGraph execution updates."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.events.research.models import ResearchEventType


class LangGraphResearchEventAdapter:
    """Maps selected graph updates to stable public runtime events.

    Internal node names, state payloads, and checkpoint records are never
    copied into ``StreamEvent.metadata``.
    """

    def initialized(self, *, research_run_id: UUID, graph_thread_id: str) -> StreamEvent:
        return StreamEvent(
            session_id=research_run_id,
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RUNTIME_INITIALIZED.value,
            metadata={"graph_thread_id": graph_thread_id, "phase": "foundation"},
        )

    def completed(self, *, research_run_id: UUID, graph_thread_id: str) -> StreamEvent:
        return StreamEvent(
            session_id=research_run_id,
            category=EventCategory.RESEARCH,
            type=ResearchEventType.RUNTIME_COMPLETED.value,
            metadata={"graph_thread_id": graph_thread_id, "phase": "foundation"},
        )

    def adapt_update(
        self,
        update: Mapping[str, object],
        *,
        research_run_id: UUID,
        graph_thread_id: str,
    ) -> StreamEvent | None:
        """Adapt only recognized lifecycle updates; omit arbitrary graph data."""

        if "initialize" in update:
            return self.initialized(
                research_run_id=research_run_id,
                graph_thread_id=graph_thread_id,
            )
        if "complete" in update:
            return self.completed(
                research_run_id=research_run_id,
                graph_thread_id=graph_thread_id,
            )
        return None

    def progress(
        self,
        *,
        research_run_id: UUID,
        event_type: ResearchEventType,
    ) -> StreamEvent:
        """Create a stable, user-safe runtime progress event.

        The intentionally small metadata shape is the public SSE/polling
        contract. Internal node names, task questions, evidence excerpts, and
        checkpoint details never cross this boundary.
        """

        labels = {
            ResearchEventType.RESEARCH_STARTED: "Research started",
            ResearchEventType.RESEARCH_COMPLETED: "Research completed",
            ResearchEventType.RESEARCH_FAILED: "Research failed",
            ResearchEventType.RUNTIME_INITIALIZED: "Research runtime initialized",
            ResearchEventType.RUNTIME_COMPLETED: "Research runtime completed",
            ResearchEventType.PLANNER_STARTED: "Planning research",
            ResearchEventType.PLANNER_COMPLETED: "Research plan ready",
            ResearchEventType.RETRIEVAL_STARTED: "Searching selected sources",
            ResearchEventType.RETRIEVAL_COMPLETED: "Source search complete",
            ResearchEventType.EVIDENCE_STARTED: "Analyzing evidence",
            ResearchEventType.EVIDENCE_COMPLETED: "Evidence analysis complete",
            ResearchEventType.REVIEW_STARTED: "Reviewing citations and coverage",
            ResearchEventType.REVIEW_COMPLETED: "Evidence review complete",
            ResearchEventType.SYNTHESIS_STARTED: "Generating report",
            ResearchEventType.SYNTHESIS_COMPLETED: "Report draft ready",
            ResearchEventType.REPORT_STARTED: "Preparing PDF",
            ResearchEventType.REPORT_COMPLETED: "Research report ready",
            ResearchEventType.RESEARCH_PAUSED: "Research paused",
            ResearchEventType.RESEARCH_RESUMED: "Resuming research",
            ResearchEventType.RESEARCH_AWAITING_APPROVAL: "Awaiting research approval",
            ResearchEventType.RESEARCH_CANCELLED: "Research cancelled",
        }
        return StreamEvent(
            session_id=research_run_id,
            category=EventCategory.RESEARCH,
            type=event_type.value,
            metadata={"label": labels[event_type]},
        )
