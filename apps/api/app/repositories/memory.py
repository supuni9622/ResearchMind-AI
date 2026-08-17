from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


class MemoryRepository:
    """
    Repository responsible for `Memory` persistence.

    This class contains only database operations.

    It must never:
        - contain business logic
        - call external services
        - commit or rollback transactions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        memory: Memory,
    ) -> Memory:
        """
        Persist a new memory row. The transaction is not committed here.
        """

        self.session.add(memory)

        await self.session.flush()
        await self.session.refresh(memory)

        return memory

    async def get_by_id_for_owner(
        self,
        *,
        memory_id: uuid.UUID,
        owner_id: uuid.UUID,
        scope_type: str = "personal",
        project_id: uuid.UUID | None = None,
    ) -> Memory | None:
        """
        Retrieve a memory by primary key, scoped to its owner so a
        caller can never load another user's memory by id.
        """

        statement = select(Memory).where(
            Memory.id == memory_id,
            Memory.owner_id == owner_id,
            Memory.scope_type == scope_type,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        types: list[str] | None = None,
        scope_type: str = "personal",
        project_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[Memory]:
        """
        List memories for an owner, optionally filtered by `Memory.type`,
        most recently updated first. Backs the non-semantic branches of
        `MemoryService.search()` (USER/RESEARCH rows have no embedding
        to rank against, so recency is the fallback ordering).
        """

        statement = (
            select(Memory)
            .where(
                Memory.owner_id == owner_id,
                Memory.scope_type == scope_type,
                Memory.project_id.is_(None)
                if project_id is None
                else Memory.project_id == project_id,
            )
            .order_by(Memory.updated_at.desc())
            .limit(limit)
        )

        if types:
            statement = statement.where(Memory.type.in_(types))

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_page_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        scope_type: str = "personal",
        project_id: uuid.UUID | None = None,
        types: list[str] | None = None,
        search: str | None = None,
        source: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """Return one owner-scoped page and its filtered total."""

        filters = [
            Memory.owner_id == owner_id,
            Memory.scope_type == scope_type,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
        ]
        if types:
            filters.append(Memory.type.in_(types))
        if search:
            filters.append(Memory.content.ilike(f"%{search}%"))
        if source:
            filters.append(Memory.memory_metadata["source"].astext == source)

        rows_statement = (
            select(Memory)
            .where(*filters)
            .order_by(Memory.updated_at.desc(), Memory.id.desc())
            .limit(limit)
            .offset(offset)
        )
        count_statement = select(func.count(Memory.id)).where(*filters)

        rows = list((await self.session.execute(rows_statement)).scalars().all())
        total = int((await self.session.execute(count_statement)).scalar_one())
        return rows, total

    async def list_stale(
        self,
        *,
        older_than: datetime,
        max_importance: float,
        types: list[str],
        owner_id: uuid.UUID | None = None,
        limit: int = 500,
    ) -> list[Memory]:
        """
        Candidates for `MemoryLifecycleService.sweep_stale()`: rows of
        the given types last touched before `older_than` and at or
        below `max_importance`. `owner_id=None` scans every owner --
        the lifecycle sweep is an administrative job, not a per-request
        operation, so unlike every other lookup here it isn't scoped to
        a single caller by default.
        """

        statement = (
            select(Memory)
            .where(
                Memory.type.in_(types),
                Memory.updated_at < older_than,
                Memory.importance_score <= max_importance,
            )
            .order_by(Memory.updated_at.asc())
            .limit(limit)
        )

        if owner_id is not None:
            statement = statement.where(Memory.owner_id == owner_id)

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def delete(
        self,
        memory: Memory,
    ) -> None:
        """
        Delete a memory row. The transaction is not committed here.
        """

        await self.session.delete(memory)
        await self.session.flush()
