from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.profile.service import UserMemoryService
from app.ai.memory.services.memory_service import MemoryService
from app.ai.memory.storage.postgres_store import PostgresMemoryStore
from app.exceptions.base import ForbiddenException
from app.models.project import Project, ProjectMembership
from app.models.user import User
from app.repositories.memory_settings import MemoryScopeSettingsRepository
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


@pytest.mark.asyncio
async def test_global_memory_is_owner_scoped_not_leaked_across_owners(
    db_session: AsyncSession,
) -> None:
    owner_a_id, owner_b_id = uuid4(), uuid4()
    db_session.add_all(
        [
            User(
                id=owner_a_id,
                auth_provider="test",
                provider_user_id=str(owner_a_id),
                email=f"{owner_a_id}@example.com",
            ),
            User(
                id=owner_b_id,
                auth_provider="test",
                provider_user_id=str(owner_b_id),
                email=f"{owner_b_id}@example.com",
            ),
        ]
    )
    await db_session.flush()

    store = PostgresMemoryStore(db_session)
    await store.create(
        owner_id=owner_a_id,
        memory_type=MemoryType.USER,
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
        content="Owner A's global preference",
        importance_score=0.9,
    )

    rows_a, total_a = await store.list_page(
        owner_id=owner_a_id,
        memory_types=[MemoryType.USER],
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
    )
    rows_b, total_b = await store.list_page(
        owner_id=owner_b_id,
        memory_types=[MemoryType.USER],
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
    )

    assert total_a == 1
    assert [row.content for row in rows_a] == ["Owner A's global preference"]
    assert rows_b == []
    assert total_b == 0


@pytest.mark.asyncio
async def test_global_memory_is_injected_into_personal_and_every_project(
    db_session: AsyncSession,
) -> None:
    """The actual GLOBAL product behavior: memory marked GLOBAL is
    injected into every context for its owner -- personal, project X, and
    project Y -- not just the scope it was written in."""

    owner_id = uuid4()
    project_x_id, project_y_id = uuid4(), uuid4()
    db_session.add(
        User(
            id=owner_id,
            auth_provider="test",
            provider_user_id=str(owner_id),
            email=f"{owner_id}@example.com",
        )
    )
    await db_session.flush()
    db_session.add_all(
        [
            Project(id=project_x_id, owner_id=owner_id, name="X"),
            Project(id=project_y_id, owner_id=owner_id, name="Y"),
        ]
    )
    await db_session.flush()

    store = PostgresMemoryStore(db_session)
    await store.create(
        owner_id=owner_id,
        memory_type=MemoryType.USER,
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
        content="Always answer in metric units",
        importance_score=0.9,
    )

    service = MemoryService(
        session_memory=AsyncMock(get_context=AsyncMock(return_value=[])),
        user_memory=UserMemoryService(store),
        semantic_memory=AsyncMock(),
        research_memory=AsyncMock(),
    )

    personal_context = await service.get_context(owner_id=owner_id, session_id=uuid4())
    project_x_context = await service.get_context(
        owner_id=owner_id,
        session_id=uuid4(),
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_x_id,
    )
    project_y_context = await service.get_context(
        owner_id=owner_id,
        session_id=uuid4(),
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_y_id,
    )

    for context in (personal_context, project_x_context, project_y_context):
        assert "Always answer in metric units" in [m.content for m in context.user_memories]


@pytest.mark.asyncio
async def test_personal_and_global_scope_settings_coexist_for_one_owner(
    db_session: AsyncSession,
) -> None:
    """Regression for a real bug found while adding GLOBAL:
    `uq_memory_scope_settings_personal` used to be `UNIQUE(owner_id)
    WHERE project_id IS NULL`, not qualified by scope_type -- a GLOBAL
    settings row would collide with the owner's PERSONAL row on that
    index. Fixed to `UNIQUE(owner_id, scope_type) WHERE project_id IS
    NULL`; this test fails with an IntegrityError without that fix."""

    owner_id = uuid4()
    db_session.add(
        User(
            id=owner_id,
            auth_provider="test",
            provider_user_id=str(owner_id),
            email=f"{owner_id}@example.com",
        )
    )
    await db_session.flush()

    repository = MemoryScopeSettingsRepository(db_session)
    await repository.upsert(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PERSONAL,
        project_id=None,
        capture_enabled=True,
        retrieval_enabled=True,
        inherit_personal_memory=True,
    )
    # Raises IntegrityError here, pre-fix, since uq_memory_scope_settings_personal
    # used to be UNIQUE(owner_id) WHERE project_id IS NULL -- not qualified
    # by scope_type -- so this second row collided with the PERSONAL one.
    await repository.upsert(
        owner_id=owner_id,
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
        capture_enabled=True,
        retrieval_enabled=False,
        inherit_personal_memory=True,
    )

    personal = await repository.get(
        owner_id=owner_id, scope_type=MemoryScopeType.PERSONAL, project_id=None
    )
    glob = await repository.get(
        owner_id=owner_id, scope_type=MemoryScopeType.GLOBAL, project_id=None
    )
    assert personal is not None and personal.retrieval_enabled is True
    assert glob is not None and glob.retrieval_enabled is False
