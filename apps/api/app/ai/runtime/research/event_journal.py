"""Persist only the public-safe runtime event contract."""

from __future__ import annotations

from uuid import UUID

from app.ai.runtime.events.research.models import ResearchEventType
from app.ai.runtime.research.events import LangGraphResearchEventAdapter
from app.repositories.research_run_event import ResearchRunEventRepository


class ResearchRuntimeEventJournal:
    def __init__(self, repository: ResearchRunEventRepository) -> None:
        self._repository = repository
        self._events = LangGraphResearchEventAdapter()

    async def publish(self, *, run_id: UUID, event_type: ResearchEventType) -> None:
        event = self._events.progress(research_run_id=run_id, event_type=event_type)
        await self._repository.append(
            run_id=run_id,
            event_type=event.type,
            metadata=event.metadata,
        )
