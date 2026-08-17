"""Portable export and immediate, auditable cross-store memory erasure."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.ai.memory.artifacts.writers import MemoryArtifactWriter
from app.ai.memory.enums import MemoryScopeType
from app.ai.memory.storage.valkey_store import ValkeySessionStore
from app.ai.memory.storage.vector_index import MemoryVectorIndex
from app.core.settings import settings
from app.exceptions.base import ConflictException, NotFoundException, ValidationException
from app.models.memory import Memory, MemoryDeletionConfirmation, MemoryGovernanceJob


class MemoryGovernanceService:
    def __init__(
        self,
        session: AsyncSession,
        vector_index: MemoryVectorIndex,
        session_store: ValkeySessionStore,
        artifact_writer: MemoryArtifactWriter,
    ) -> None:
        self._session = session
        self._vector_index = vector_index
        self._session_store = session_store
        self._artifact_writer = artifact_writer

    @staticmethod
    def _scope_filters(
        owner_id: UUID, scope_type: MemoryScopeType, project_id: UUID | None
    ) -> list[ColumnElement[bool]]:
        return [
            Memory.owner_id == owner_id,
            Memory.scope_type == scope_type.value,
            Memory.project_id.is_(None) if project_id is None else Memory.project_id == project_id,
        ]

    async def export_scope(
        self, *, owner_id: UUID, scope_type: MemoryScopeType, project_id: UUID | None
    ) -> list[Memory]:
        statement = (
            select(Memory)
            .where(*self._scope_filters(owner_id, scope_type, project_id))
            .order_by(Memory.created_at.asc(), Memory.id.asc())
        )
        return list((await self._session.execute(statement)).scalars().all())

    async def preview_deletion(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        memory_ids: list[UUID] | None,
    ) -> tuple[str, MemoryDeletionConfirmation]:
        filters = self._scope_filters(owner_id, scope_type, project_id)
        if memory_ids is not None:
            if not memory_ids:
                raise ValidationException(message="Select at least one memory to delete.")
            filters.append(Memory.id.in_(memory_ids))
        ids = list((await self._session.execute(select(Memory.id).where(*filters))).scalars().all())
        if memory_ids is not None and len(ids) != len(set(memory_ids)):
            raise NotFoundException(message="One or more selected memories were not found.")
        token = secrets.token_urlsafe(32)
        confirmation = MemoryDeletionConfirmation(
            id=uuid4(),
            owner_id=owner_id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            scope_type=scope_type.value,
            project_id=project_id,
            memory_ids=[str(item) for item in ids] if memory_ids is not None else None,
            expected_count=len(ids),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=settings.memory_deletion_confirmation_ttl_seconds),
        )
        self._session.add(confirmation)
        await self._session.commit()
        return token, confirmation

    async def execute_deletion(self, *, owner_id: UUID, token: str) -> MemoryGovernanceJob:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        confirmation = (
            await self._session.execute(
                select(MemoryDeletionConfirmation).where(
                    MemoryDeletionConfirmation.owner_id == owner_id,
                    MemoryDeletionConfirmation.token_hash == token_hash,
                )
            )
        ).scalar_one_or_none()
        if confirmation is None:
            raise ValidationException(message="Deletion confirmation is invalid.")
        existing = (
            await self._session.execute(
                select(MemoryGovernanceJob).where(
                    MemoryGovernanceJob.confirmation_id == confirmation.id
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        if confirmation.expires_at <= now or confirmation.consumed_at is not None:
            raise ValidationException(message="Deletion confirmation has expired or was used.")
        confirmation.consumed_at = now
        job = MemoryGovernanceJob(
            id=uuid4(),
            owner_id=owner_id,
            confirmation_id=confirmation.id,
            scope_type=confirmation.scope_type,
            project_id=confirmation.project_id,
            status="running",
            requested_count=confirmation.expected_count,
        )
        self._session.add(job)
        await self._session.commit()
        return await self._run(job, confirmation)

    async def retry(self, *, owner_id: UUID, job_id: UUID) -> MemoryGovernanceJob:
        job = await self.get_job(owner_id=owner_id, job_id=job_id)
        if job.status != "failed":
            return job
        confirmation = await self._session.get(MemoryDeletionConfirmation, job.confirmation_id)
        if confirmation is None:
            raise ConflictException(message="Deletion confirmation audit record is unavailable.")
        job.status = "running"
        job.failure_stage = None
        job.failure_detail = None
        await self._session.commit()
        return await self._run(job, confirmation)

    async def get_job(self, *, owner_id: UUID, job_id: UUID) -> MemoryGovernanceJob:
        job = (
            await self._session.execute(
                select(MemoryGovernanceJob).where(
                    MemoryGovernanceJob.id == job_id, MemoryGovernanceJob.owner_id == owner_id
                )
            )
        ).scalar_one_or_none()
        if job is None:
            raise NotFoundException(message="Memory deletion job was not found.")
        return job

    async def _run(
        self, job: MemoryGovernanceJob, confirmation: MemoryDeletionConfirmation
    ) -> MemoryGovernanceJob:
        scope_type = MemoryScopeType(confirmation.scope_type)
        filters = self._scope_filters(job.owner_id, scope_type, confirmation.project_id)
        if confirmation.memory_ids is not None:
            filters.append(Memory.id.in_([UUID(item) for item in confirmation.memory_ids]))
        rows = list((await self._session.execute(select(Memory).where(*filters))).scalars().all())
        vector_ids = [row.id for row in rows if row.type in {"semantic", "research"}]
        try:
            for memory_id in vector_ids:
                if not await self._vector_index.delete(memory_id):
                    raise RuntimeError(f"Qdrant did not confirm deletion for {memory_id}")
            job.deleted_qdrant += len(vector_ids)
        except Exception as exc:
            return await self._fail(job, "qdrant", exc)
        try:
            result = await self._session.execute(delete(Memory).where(*filters))
            job.deleted_postgres += int(result.rowcount or 0)  # type: ignore[attr-defined]
            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            return await self._fail(job, "postgres", exc)
        if confirmation.memory_ids is None:
            try:
                job.deleted_valkey += await self._session_store.purge_scope(
                    owner_id=job.owner_id,
                    scope_type=scope_type,
                    project_id=confirmation.project_id,
                )
            except Exception as exc:
                return await self._fail(job, "valkey", exc)
        try:
            # Artifacts can embed several retrieved memories; selective object
            # deletion cannot prove which files contain one selected ID, so
            # erase the scope's derived memory artifacts conservatively.
            job.deleted_artifacts += await self._artifact_writer.purge_scope(
                owner_id=job.owner_id,
                scope_type=scope_type.value,
                project_id=confirmation.project_id,
            )
        except Exception as exc:
            return await self._fail(job, "artifacts", exc)
        remaining = int(
            len(
                list(
                    (await self._session.execute(select(Memory.id).where(*filters))).scalars().all()
                )
            )
        )
        if remaining:
            return await self._fail(job, "verification", RuntimeError(f"{remaining} rows remain"))
        job.status = "completed"
        job.completed_at = datetime.now(UTC)
        await self._session.commit()
        return job

    async def _fail(
        self, job: MemoryGovernanceJob, stage: str, exc: Exception
    ) -> MemoryGovernanceJob:
        job.status = "failed"
        job.failure_stage = stage
        job.failure_detail = str(exc)[:500]
        await self._session.commit()
        return job
