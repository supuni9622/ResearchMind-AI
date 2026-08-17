from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.enums import MemoryScopeType
from app.exceptions.base import ForbiddenException, ValidationException
from app.models.project import Project, ProjectMembership


class ProjectAuthorizationService:
    """Resolve and authorize a memory scope before storage access."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_accessible_projects(self, *, user_id: UUID) -> list[tuple[Project, str]]:
        membership = ProjectMembership
        statement = (
            select(Project, membership.role)
            .outerjoin(
                membership,
                (membership.project_id == Project.id) & (membership.user_id == user_id),
            )
            .where(or_(Project.owner_id == user_id, membership.user_id == user_id))
            .order_by(Project.name.asc(), Project.id.asc())
        )
        rows = (await self._session.execute(statement)).all()
        return [
            (project, "owner" if project.owner_id == user_id else role) for project, role in rows
        ]

    async def authorize_memory_scope(
        self,
        *,
        user_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> None:
        if scope_type == MemoryScopeType.PERSONAL:
            if project_id is not None:
                raise ValidationException(message="project_id is not allowed for personal memory")
            return
        if project_id is None:
            raise ValidationException(message="project_id is required for project memory")

        statement = select(
            exists().where(
                Project.id == project_id,
                or_(
                    Project.owner_id == user_id,
                    exists().where(
                        ProjectMembership.project_id == project_id,
                        ProjectMembership.user_id == user_id,
                    ),
                ),
            )
        )
        if not bool((await self._session.execute(statement)).scalar()):
            # Do not disclose whether a project exists.
            raise ForbiddenException(message="Project memory access is not permitted.")
