"""
Shared Postgres CRUD for USER/RESEARCH/SEMANTIC memory (PRD §6.2/§6.3/
§6.4 all name Postgres as a storage backend). `UserMemoryService`,
`SemanticMemoryService`, and `ResearchMemoryService` are otherwise
identical at the storage layer -- differing only in whether they also
maintain a Qdrant search index on top -- so this one class holds the
Postgres side for all three rather than duplicating it three times.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryRecord
from app.models.memory import Memory
from app.repositories.memory import MemoryRepository


class PostgresMemoryStore:
    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self._session = session
        self._repository = MemoryRepository(session)

    async def create(
        self,
        *,
        owner_id: UUID,
        memory_type: MemoryType,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        content: str,
        importance_score: float,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryRecord:
        now = datetime.now(UTC)

        row = await self._repository.create(
            Memory(
                id=uuid4(),
                owner_id=owner_id,
                scope_type=scope_type.value,
                project_id=project_id,
                type=memory_type.value,
                content=content,
                memory_metadata=metadata or {},
                importance_score=importance_score,
                created_at=now,
                updated_at=now,
            )
        )

        await self._session.commit()

        return self._to_record(row)

    async def get(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        row = await self._repository.get_by_id_for_owner(
            memory_id=memory_id,
            owner_id=owner_id,
            scope_type=scope_type.value,
            project_id=project_id,
        )

        return self._to_record(row) if row is not None else None

    async def list_by_type(
        self,
        *,
        owner_id: UUID,
        memory_type: MemoryType,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        limit: int = 100,
    ) -> list[MemoryRecord]:
        rows = await self._repository.list_for_owner(
            owner_id=owner_id,
            types=[memory_type.value],
            scope_type=scope_type.value,
            project_id=project_id,
            limit=limit,
        )

        return [self._to_record(row) for row in rows]

    async def list_page_by_type(
        self,
        *,
        owner_id: UUID,
        memory_type: MemoryType,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        search: str | None = None,
        source: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        origin: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        rows, total = await self._repository.list_page_for_owner(
            owner_id=owner_id,
            types=[memory_type.value],
            scope_type=scope_type.value,
            project_id=project_id,
            search=search,
            source=source,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            origin=origin,
            limit=limit,
            offset=offset,
        )
        return [self._to_record(row) for row in rows], total

    async def list_page(
        self,
        *,
        owner_id: UUID,
        memory_types: list[MemoryType] | None,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        search: str | None = None,
        source: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        origin: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MemoryRecord], int]:
        rows, total = await self._repository.list_page_for_owner(
            owner_id=owner_id,
            types=[item.value for item in memory_types] if memory_types else None,
            scope_type=scope_type.value,
            project_id=project_id,
            search=search,
            source=source,
            created_from=created_from,
            created_to=created_to,
            updated_from=updated_from,
            updated_to=updated_to,
            origin=origin,
            limit=limit,
            offset=offset,
        )
        return [self._to_record(row) for row in rows], total

    async def count_scope(
        self, *, owner_id: UUID, scope_type: MemoryScopeType, project_id: UUID | None
    ) -> int:
        statement = select(func.count(Memory.id)).where(
            Memory.owner_id == owner_id,
            Memory.scope_type == scope_type.value,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
        )
        return int((await self._session.execute(statement)).scalar_one())

    async def list_user_preference_candidates(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        preference_key: str,
        search_terms: list[str],
        limit: int,
    ) -> list[MemoryRecord]:
        rows = await self._repository.list_user_preference_candidates(
            owner_id=owner_id,
            scope_type=scope_type.value,
            project_id=project_id,
            preference_key=preference_key,
            search_terms=search_terms,
            limit=limit,
        )
        return [self._to_record(row) for row in rows]

    async def exists_for_owner(
        self,
        *,
        owner_id: UUID,
        memory_types: set[MemoryType],
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool:
        """Whether an owner has any durable memories of the given types."""

        if not memory_types:
            return False

        statement = select(
            exists().where(
                Memory.owner_id == owner_id,
                Memory.scope_type == scope_type.value,
                Memory.project_id.is_(None)
                if project_id is None
                else Memory.project_id == project_id,
                Memory.type.in_([memory_type.value for memory_type in memory_types]),
                Memory.memory_metadata["_consolidated_into"].astext.is_(None),
            )
        )
        return bool((await self._session.execute(statement)).scalar())

    async def find_exact_content(
        self,
        *,
        owner_id: UUID,
        memory_type: MemoryType,
        content: str,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> MemoryRecord | None:
        """Find an exact normalized durable memory for safe de-duplication.

        We intentionally do not use semantic similarity to decide whether a
        new fact supersedes an old one. That needs an explicit subject/version
        model and would be unsafe to infer in the response path.
        """

        normalized = " ".join(content.lower().split())
        statement = select(Memory).where(
            Memory.owner_id == owner_id,
            Memory.type == memory_type.value,
            Memory.scope_type == scope_type.value,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
            func.lower(func.trim(Memory.content)) == normalized,
            Memory.memory_metadata["_consolidated_into"].astext.is_(None),
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        return self._to_record(row) if row is not None else None

    async def update(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float | None = None,
    ) -> MemoryRecord | None:
        row = await self._repository.get_by_id_for_owner(
            memory_id=memory_id,
            owner_id=owner_id,
            scope_type=scope_type.value,
            project_id=project_id,
        )

        if row is None:
            return None

        if content is not None:
            row.content = content

        if metadata is not None:
            row.memory_metadata = {**row.memory_metadata, **metadata}

        if importance_score is not None:
            row.importance_score = importance_score

        row.updated_at = datetime.now(UTC)

        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(row)

        return self._to_record(row)

    async def delete(
        self,
        *,
        owner_id: UUID,
        memory_id: UUID,
        scope_type: MemoryScopeType = MemoryScopeType.PERSONAL,
        project_id: UUID | None = None,
    ) -> bool:
        row = await self._repository.get_by_id_for_owner(
            memory_id=memory_id,
            owner_id=owner_id,
            scope_type=scope_type.value,
            project_id=project_id,
        )

        if row is None:
            return False

        await self._repository.delete(row)
        await self._session.commit()

        return True

    @staticmethod
    def _to_record(row: Memory) -> MemoryRecord:
        return MemoryRecord(
            id=row.id,
            owner_id=row.owner_id,
            scope_type=MemoryScopeType(row.scope_type),
            project_id=row.project_id,
            type=MemoryType(row.type),
            content=row.content,
            metadata=row.memory_metadata,
            importance_score=row.importance_score,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
