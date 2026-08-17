from __future__ import annotations

from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.exceptions.base import ForbiddenException
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.services.project_authorization import ProjectAuthorizationService
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_two_users_and_two_projects_cannot_enumerate_each_others_memory(
    db_session: AsyncSession,
) -> None:
    user_a_id, user_b_id = uuid4(), uuid4()
    project_a_id, project_b_id = uuid4(), uuid4()
    db_session.add_all(
        [
            User(
                id=user_a_id,
                auth_provider="test",
                provider_user_id=str(user_a_id),
                email=f"{user_a_id}@example.com",
            ),
            User(
                id=user_b_id,
                auth_provider="test",
                provider_user_id=str(user_b_id),
                email=f"{user_b_id}@example.com",
            ),
        ]
    )
    await db_session.flush()
    db_session.add_all(
        [
            Project(id=project_a_id, owner_id=user_a_id, name="A"),
            Project(id=project_b_id, owner_id=user_b_id, name="B"),
        ]
    )
    await db_session.flush()
    store = PostgresMemoryStore(db_session)
    await store.create(
        owner_id=user_a_id,
        memory_type=MemoryType.USER,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_a_id,
        content="A private project preference",
        importance_score=0.9,
    )
    await store.create(
        owner_id=user_b_id,
        memory_type=MemoryType.USER,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_b_id,
        content="B private project preference",
        importance_score=0.9,
    )

    rows_a, total_a = await store.list_page(
        owner_id=user_a_id,
        memory_types=[MemoryType.USER],
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_a_id,
    )
    leaked_rows, leaked_total = await store.list_page(
        owner_id=user_a_id,
        memory_types=[MemoryType.USER],
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_b_id,
    )

    assert total_a == 1
    assert [row.content for row in rows_a] == ["A private project preference"]
    assert leaked_rows == []
    assert leaked_total == 0
    with pytest.raises(ForbiddenException):
        await ProjectAuthorizationService(db_session).authorize_memory_scope(
            user_id=user_a_id,
            scope_type=MemoryScopeType.PROJECT,
            project_id=project_b_id,
        )


@pytest.mark.asyncio
async def test_project_member_access_does_not_change_memory_ownership(
    db_session: AsyncSession,
) -> None:
    owner_id, member_id = uuid4(), uuid4()
    project_id = uuid4()
    db_session.add_all(
        [
            User(
                id=owner_id,
                auth_provider="test",
                provider_user_id=str(owner_id),
                email=f"{owner_id}@example.com",
            ),
            User(
                id=member_id,
                auth_provider="test",
                provider_user_id=str(member_id),
                email=f"{member_id}@example.com",
            ),
        ]
    )
    await db_session.flush()
    db_session.add(Project(id=project_id, owner_id=owner_id, name="Shared"))
    await db_session.flush()
    db_session.add(ProjectMembership(project_id=project_id, user_id=member_id, role="member"))
    await db_session.flush()
    authorization = ProjectAuthorizationService(db_session)
    await authorization.authorize_memory_scope(
        user_id=member_id,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
    )

    store = PostgresMemoryStore(db_session)
    await store.create(
        owner_id=owner_id,
        memory_type=MemoryType.RESEARCH,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
        content="Owner-authored project finding",
        importance_score=0.9,
    )
    member_rows, member_total = await store.list_page(
        owner_id=member_id,
        memory_types=[MemoryType.RESEARCH],
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
    )

    assert member_rows == []
    assert member_total == 0
