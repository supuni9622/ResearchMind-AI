from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.enums import MemoryScopeType
from app.models.memory import MemoryScopeSetting


class MemoryScopeSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> MemoryScopeSetting | None:
        statement = select(MemoryScopeSetting).where(
            MemoryScopeSetting.owner_id == owner_id,
            MemoryScopeSetting.scope_type == scope_type.value,
            MemoryScopeSetting.project_id.is_(None)
            if project_id is None
            else MemoryScopeSetting.project_id == project_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none()

    async def upsert(
        self,
        *,
        owner_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
        capture_enabled: bool,
        retrieval_enabled: bool,
        inherit_personal_memory: bool,
    ) -> MemoryScopeSetting:
        row = await self.get(owner_id=owner_id, scope_type=scope_type, project_id=project_id)
        if row is None:
            row = MemoryScopeSetting(
                owner_id=owner_id,
                scope_type=scope_type.value,
                project_id=project_id,
                capture_enabled=capture_enabled,
                retrieval_enabled=retrieval_enabled,
                inherit_personal_memory=inherit_personal_memory,
            )
            self._session.add(row)
        else:
            row.capture_enabled = capture_enabled
            row.retrieval_enabled = retrieval_enabled
            row.inherit_personal_memory = inherit_personal_memory
        await self._session.commit()
        await self._session.refresh(row)
        return row
