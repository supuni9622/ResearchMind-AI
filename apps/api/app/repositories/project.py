from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMembership


class ProjectRepository:
    """
    Repository responsible for Project persistence.

    This class contains only database operations.

    It must never:
        - contain business logic
        - call external services
        - commit or rollback transactions
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, project: Project) -> Project:
        """Persist a new project. The transaction is not committed here."""

        self.session.add(project)

        await self.session.flush()
        await self.session.refresh(project)

        return project

    async def get_by_id(self, *, project_id: uuid.UUID) -> Project | None:
        statement = select(Project).where(Project.id == project_id)

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[tuple[Project, str]]:
        """Every project a user can see -- owned outright, or via membership.

        Returns `(project, role)` pairs; `role` is the raw membership role
        for a non-owner ("owner" is derived by the caller by comparing
        `project.owner_id == user_id`, not stored here, since an owner has
        no membership row).
        """

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
        rows = (await self.session.execute(statement)).all()
        return [(project, role) for project, role in rows]

    async def update(self, project: Project) -> Project:
        """Persist changes to an already-loaded project. Not committed here."""

        await self.session.flush()
        await self.session.refresh(project)

        return project

    async def delete(self, project: Project) -> None:
        """Delete a project. The transaction is not committed here."""

        await self.session.delete(project)
        await self.session.flush()
