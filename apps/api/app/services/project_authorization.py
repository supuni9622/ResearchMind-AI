from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.enums import MemoryScopeType
from app.exceptions.base import ForbiddenException, ValidationException
from app.models.project import Project, ProjectMembership
from app.repositories.project import ProjectRepository


class ProjectAuthorizationService:
    """Resolve and authorize access to a project, and its memory scope."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = ProjectRepository(session)

    async def list_accessible_projects(self, *, user_id: UUID) -> list[tuple[Project, str]]:
        rows = await self._repository.list_for_user(user_id=user_id)
        return [
            (project, "owner" if project.owner_id == user_id else role) for project, role in rows
        ]

    async def authorize_project_access(self, *, user_id: UUID, project_id: UUID) -> None:
        """Generic, non-memory-specific project access check: owner or member."""

        if not await self._user_has_access(user_id=user_id, project_id=project_id):
            # Do not disclose whether a project exists.
            raise ForbiddenException(message="Project access is not permitted.")

    async def authorize_for_new_conversation(
        self,
        *,
        conversation_id: UUID | None,
        project_id: UUID | None,
        user_id: UUID,
    ) -> None:
        """Authorize `project_id` before a *new* conversation is created
        with it -- shared by Chat and Research, both of which mint a new
        conversation/thread when `conversation_id` is omitted.

        Only relevant on the create branch -- an existing conversation
        (`conversation_id` given) already carries its own stored
        `project_id`, authorized once at its own creation time;
        re-checking every turn would be redundant (ownership via each
        surface's own owner-scoped lookup already gates access, and
        there's no membership-revocation UI yet to make that check stale).
        """

        if conversation_id is not None or project_id is None:
            return

        await self.authorize_project_access(user_id=user_id, project_id=project_id)

    async def authorize_memory_scope(
        self,
        *,
        user_id: UUID,
        scope_type: MemoryScopeType,
        project_id: UUID | None,
    ) -> None:
        if scope_type != MemoryScopeType.PROJECT:
            # PERSONAL and GLOBAL: owner-scoped only, no project_id, no
            # membership check -- GLOBAL is never project-gated.
            if project_id is not None:
                raise ValidationException(
                    message="project_id is not allowed for personal or global memory"
                )
            return
        if project_id is None:
            raise ValidationException(message="project_id is required for project memory")

        if not await self._user_has_access(user_id=user_id, project_id=project_id):
            # Do not disclose whether a project exists.
            raise ForbiddenException(message="Project memory access is not permitted.")

    async def _user_has_access(self, *, user_id: UUID, project_id: UUID) -> bool:
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
        return bool((await self._session.execute(statement)).scalar())
