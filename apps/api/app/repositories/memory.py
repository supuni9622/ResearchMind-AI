from __future__ import annotations

import uuid
from datetime import datetime
from typing import TypedDict, cast

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.memory import Memory


class MemoryObservabilitySnapshot(TypedDict):
    counts: dict[tuple[str, str], int]
    oldest_age_seconds: dict[str, float]
    sizes: dict[str, int]
    distributions: dict[tuple[str, str], float]


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

    @staticmethod
    def _active_filter() -> ColumnElement[bool]:
        """Hide lineage rows archived by consolidation from normal reads."""

        return cast(
            ColumnElement[bool],
            Memory.memory_metadata["_consolidated_into"].astext.is_(None),
        )

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
            self._active_filter(),
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
                self._active_filter(),
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
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        updated_from: datetime | None = None,
        updated_to: datetime | None = None,
        origin: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        """Return one owner-scoped page and its filtered total."""

        filters = [
            Memory.owner_id == owner_id,
            Memory.scope_type == scope_type,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
            self._active_filter(),
        ]
        if types:
            filters.append(Memory.type.in_(types))
        if search:
            filters.append(Memory.content.ilike(f"%{search}%"))
        if source:
            filters.append(Memory.memory_metadata["source"].astext == source)
        if created_from:
            filters.append(Memory.created_at >= created_from)
        if created_to:
            filters.append(Memory.created_at <= created_to)
        if updated_from:
            filters.append(Memory.updated_at >= updated_from)
        if updated_to:
            filters.append(Memory.updated_at <= updated_to)
        if origin == "explicit":
            filters.append(
                or_(
                    Memory.memory_metadata["origin"].astext == "explicit",
                    Memory.memory_metadata["preference"]["explicit"].astext == "true",
                    Memory.memory_metadata["source"].astext == "manual",
                )
            )
        elif origin == "inferred":
            filters.append(
                or_(
                    Memory.memory_metadata["origin"].astext == "inferred",
                    Memory.memory_metadata["preference"]["explicit"].astext == "false",
                    Memory.memory_metadata["source"].astext == "extraction",
                )
            )

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

    async def list_user_preference_candidates(
        self,
        *,
        owner_id: uuid.UUID,
        scope_type: str,
        project_id: uuid.UUID | None,
        preference_key: str,
        search_terms: list[str],
        limit: int,
    ) -> list[Memory]:
        """Nominate historical USER preferences by topic, not recency.

        This query remains strictly tenant/scope bounded. Matching only
        nominates rows; the structured supersession judge remains the authority
        that can approve an update-in-place.
        """

        key_match = Memory.memory_metadata["preference_key"].astext == preference_key
        topical_matches = [Memory.content.ilike(f"%{term}%") for term in search_terms]
        statement = (
            select(Memory)
            .where(
                Memory.owner_id == owner_id,
                Memory.scope_type == scope_type,
                Memory.project_id.is_(None)
                if project_id is None
                else Memory.project_id == project_id,
                Memory.type == "user",
                self._active_filter(),
                or_(key_match, *topical_matches),
            )
            .order_by(case((key_match, 0), else_=1), Memory.updated_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def list_vector_memory_ids(self) -> set[uuid.UUID]:
        """Canonical IDs that must have a Qdrant point (admin inventory path)."""

        statement = select(Memory.id).where(
            Memory.type.in_(("semantic", "research")),
            self._active_filter(),
        )
        return set((await self.session.execute(statement)).scalars().all())

    async def memory_observability_snapshot(self) -> MemoryObservabilitySnapshot:
        """Bounded aggregate storage facts; never returns tenant identifiers."""

        counts = {
            (str(memory_type), str(scope_type)): int(count)
            for memory_type, scope_type, count in (
                await self.session.execute(
                    select(Memory.type, Memory.scope_type, func.count(Memory.id)).group_by(
                        Memory.type, Memory.scope_type
                    )
                )
            ).all()
        }
        oldest_age_seconds = {
            str(memory_type): float(age or 0.0)
            for memory_type, age in (
                await self.session.execute(
                    select(
                        Memory.type,
                        func.extract("epoch", func.now() - func.min(Memory.created_at)),
                    ).group_by(Memory.type)
                )
            ).all()
        }
        sizes = (
            await self.session.execute(
                text(
                    "SELECT pg_relation_size('memories') AS table_bytes, "
                    "pg_indexes_size('memories') AS index_bytes, "
                    "pg_total_relation_size('memories') AS total_bytes"
                )
            )
        ).one()
        distribution_rows = (
            await self.session.execute(
                text(
                    "WITH owner_counts AS ("
                    " SELECT owner_id, count(*)::double precision AS n FROM memories "
                    " GROUP BY owner_id"
                    "), project_counts AS ("
                    " SELECT project_id, count(*)::double precision AS n FROM memories "
                    " WHERE project_id IS NOT NULL GROUP BY project_id"
                    ") "
                    "SELECT 'owner' AS dimension, "
                    " coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY n), 0) AS p50, "
                    " coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY n), 0) AS p95, "
                    " coalesce(max(n), 0) AS maximum FROM owner_counts "
                    "UNION ALL SELECT 'project', "
                    " coalesce(percentile_cont(0.5) WITHIN GROUP (ORDER BY n), 0), "
                    " coalesce(percentile_cont(0.95) WITHIN GROUP (ORDER BY n), 0), "
                    " coalesce(max(n), 0) FROM project_counts"
                )
            )
        ).all()
        distributions = {
            (str(dimension), quantile): float(value)
            for dimension, p50, p95, maximum in distribution_rows
            for quantile, value in (("p50", p50), ("p95", p95), ("max", maximum))
        }
        return {
            "counts": counts,
            "oldest_age_seconds": oldest_age_seconds,
            "sizes": {
                "table": int(sizes.table_bytes),
                "index": int(sizes.index_bytes),
                "total": int(sizes.total_bytes),
            },
            "distributions": distributions,
        }

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
                self._active_filter(),
            )
            .order_by(Memory.updated_at.asc())
            .limit(limit)
        )

        if owner_id is not None:
            statement = statement.where(Memory.owner_id == owner_id)

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def list_consolidation_seeds(self, *, types: list[str], limit: int) -> list[Memory]:
        """Return active, not-yet-reviewed rows across tenants for the admin worker."""

        statement = (
            select(Memory)
            .where(
                Memory.type.in_(types),
                self._active_filter(),
                Memory.memory_metadata["_consolidation_checked_at"].astext.is_(None),
            )
            .order_by(Memory.created_at.asc(), Memory.id.asc())
            .limit(limit)
        )
        return list((await self.session.execute(statement)).scalars().all())

    async def delete(
        self,
        memory: Memory,
    ) -> None:
        """
        Delete a memory row. The transaction is not committed here.
        """

        await self.session.delete(memory)
        await self.session.flush()
