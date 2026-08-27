"""Isolated persistence for preferences learned from user feedback."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.memory.create import build_memory_service
from app.ai.memory.enums import MemoryType
from app.ai.memory.services.memory_service import MemoryService
from app.models.enums import FeedbackSurface


class PreferenceMemoryWriterProtocol(Protocol):
    """Port used by feedback without sharing its database transaction."""

    async def remember_feedback_preference(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        content: str,
        importance_score: float,
    ) -> None: ...


class PreferenceMemoryWriter:
    """Write one USER preference in a separately owned unit of work.

    The caller commits canonical feedback before invoking this writer. This
    class deliberately creates, commits, rolls back, and closes its own
    session, so a failed best-effort memory write cannot poison or roll back
    the feedback transaction.
    """

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        memory_service_factory: Callable[[AsyncSession], MemoryService] = build_memory_service,
    ) -> None:
        self._session_factory = session_factory
        self._memory_service_factory = memory_service_factory

    async def remember_feedback_preference(
        self,
        *,
        owner_id: UUID,
        generation_id: UUID,
        surface: FeedbackSurface,
        content: str,
        importance_score: float,
    ) -> None:
        async with self._session_factory() as session:
            try:
                memory_service = self._memory_service_factory(session)
                await memory_service.remember_extracted(
                    owner_id=owner_id,
                    type=MemoryType.USER,
                    content=content,
                    importance_score=importance_score,
                    metadata={
                        "source": "feedback",
                        "generation_id": str(generation_id),
                        "surface": surface.value,
                    },
                )
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
