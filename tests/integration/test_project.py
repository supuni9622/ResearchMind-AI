"""Integration tests for the Project workspace repository/service layer,
against a real Postgres session -- mirrors tests/integration/test_memory.py's
fixture style (the closest existing precedent for Project/ProjectMembership
coverage)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.exceptions.base import ForbiddenException, NotFoundException
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.repositories.project import ProjectRepository
from app.services.project import ProjectService
from sqlalchemy.ext.asyncio import AsyncSession


def _make_user(user_id: object) -> User:
    return User(
        id=user_id,
        auth_provider="test",
        provider_user_id=str(user_id),
        email=f"{user_id}@example.com",
    )


@pytest.mark.asyncio
async def test_create_then_get_for_user_round_trips(db_session: AsyncSession) -> None:
    owner_id = uuid4()
    db_session.add(_make_user(owner_id))
    await db_session.flush()

    service = ProjectService(db_session)
    created = await service.create(owner_id=owner_id, name="Alpha", description="First project")

    fetched = await service.get_for_user(user_id=owner_id, project_id=created.id)

    assert fetched.id == created.id
    assert fetched.name == "Alpha"
    assert fetched.description == "First project"


@pytest.mark.asyncio
async def test_non_member_cannot_read_or_mutate_another_owners_project(
    db_session: AsyncSession,
) -> None:
    owner_id, stranger_id = uuid4(), uuid4()
    db_session.add_all([_make_user(owner_id), _make_user(stranger_id)])
    await db_session.flush()

    service = ProjectService(db_session)
    project = await service.create(owner_id=owner_id, name="Private", description=None)

    with pytest.raises(ForbiddenException):
        await service.get_for_user(user_id=stranger_id, project_id=project.id)
    with pytest.raises(ForbiddenException):
        await service.update(
            owner_id=stranger_id, project_id=project.id, name="Hijacked", description=None
        )
    with pytest.raises(ForbiddenException):
        await service.delete(owner_id=stranger_id, project_id=project.id)


@pytest.mark.asyncio
async def test_member_can_read_but_not_mutate(db_session: AsyncSession) -> None:
    owner_id, member_id = uuid4(), uuid4()
    db_session.add_all([_make_user(owner_id), _make_user(member_id)])
    await db_session.flush()

    service = ProjectService(db_session)
    project = await service.create(owner_id=owner_id, name="Shared", description=None)
    db_session.add(ProjectMembership(project_id=project.id, user_id=member_id, role="member"))
    await db_session.flush()

    # Read access: owner-or-member.
    fetched = await service.get_for_user(user_id=member_id, project_id=project.id)
    assert fetched.id == project.id

    # Mutation: owner-only -- no membership-management UI exists yet to make
    # a non-owner member a meaningful actor for update/delete.
    with pytest.raises(ForbiddenException):
        await service.update(
            owner_id=member_id, project_id=project.id, name="Renamed", description=None
        )


@pytest.mark.asyncio
async def test_delete_missing_project_raises_not_found(db_session: AsyncSession) -> None:
    owner_id = uuid4()
    db_session.add(_make_user(owner_id))
    await db_session.flush()

    service = ProjectService(db_session)

    with pytest.raises(NotFoundException):
        await service.delete(owner_id=owner_id, project_id=uuid4())


@pytest.mark.asyncio
async def test_list_for_user_includes_owned_and_member_projects(db_session: AsyncSession) -> None:
    owner_id, member_id, stranger_id = uuid4(), uuid4(), uuid4()
    db_session.add_all([_make_user(owner_id), _make_user(member_id), _make_user(stranger_id)])
    await db_session.flush()

    service = ProjectService(db_session)
    owned = await service.create(owner_id=owner_id, name="Owned", description=None)
    shared = await service.create(owner_id=owner_id, name="Shared", description=None)
    await service.create(owner_id=stranger_id, name="Not visible", description=None)
    db_session.add(ProjectMembership(project_id=shared.id, user_id=member_id, role="member"))
    await db_session.flush()

    owner_view = {p.id: role for p, role in await service.list_for_user(user_id=owner_id)}
    member_view = {p.id: role for p, role in await service.list_for_user(user_id=member_id)}

    assert owner_view == {owned.id: "owner", shared.id: "owner"}
    assert member_view == {shared.id: "member"}


@pytest.mark.asyncio
async def test_repository_delete_removes_row(db_session: AsyncSession) -> None:
    owner_id = uuid4()
    db_session.add(_make_user(owner_id))
    await db_session.flush()

    repository = ProjectRepository(db_session)
    project = await repository.create(Project(owner_id=owner_id, name="Temp"))
    project_id = project.id

    await repository.delete(project)

    assert await repository.get_by_id(project_id=project_id) is None
