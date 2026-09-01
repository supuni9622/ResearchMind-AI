from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import ForbiddenException, NotFoundException
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.services.project_authorization import ProjectAuthorizationService


class ProjectService:
    """
    Service responsible for Project business logic.

    Services coordinate repositories,
    enforce business rules,
    and manage database transactions.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProjectRepository(session)
        self.authorization = ProjectAuthorizationService(session)

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        description: str | None,
    ) -> Project:
        project = await self.repository.create(
            Project(owner_id=owner_id, name=name, description=description),
        )

        await self.session.commit()

        return project

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[tuple[Project, str]]:
        return await self.authorization.list_accessible_projects(user_id=user_id)

    async def get_for_user(
        self,
        *,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
    ) -> Project:
        """Owner-or-member read access."""

        await self.authorization.authorize_project_access(user_id=user_id, project_id=project_id)

        project = await self.repository.get_by_id(project_id=project_id)
        if project is None:
            raise NotFoundException(message=f"Project '{project_id}' was not found.")

        return project

    async def update(
        self,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str | None,
        description: str | None,
    ) -> Project:
        """Owner-only -- no membership-management UI exists yet to make a
        non-owner member a meaningful actor for mutating a project."""

        project = await self._get_owned(owner_id=owner_id, project_id=project_id)

        if name is not None:
            project.name = name
        if description is not None:
            project.description = description

        project = await self.repository.update(project)
        await self.session.commit()

        return project

    async def delete(self, *, owner_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Owner-only. Conversations detach (ON DELETE SET NULL); project-scoped
        memory cascades -- both handled by the FK constraints, not here."""

        project = await self._get_owned(owner_id=owner_id, project_id=project_id)

        await self.repository.delete(project)
        await self.session.commit()

    async def _get_owned(self, *, owner_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        project = await self.repository.get_by_id(project_id=project_id)
        if project is None:
            raise NotFoundException(message=f"Project '{project_id}' was not found.")
        if project.owner_id != owner_id:
            raise ForbiddenException(message="Only the project owner can do this.")

        return project
