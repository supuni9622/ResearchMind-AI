from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType
from app.exceptions.base import ForbiddenException, ValidationException
from app.services.project_authorization import ProjectAuthorizationService


@pytest.mark.asyncio
async def test_personal_scope_never_queries_project_membership() -> None:
    session = AsyncMock()
    service = ProjectAuthorizationService(session)

    await service.authorize_memory_scope(
        user_id=uuid4(), scope_type=MemoryScopeType.PERSONAL, project_id=None
    )

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_project_scope_allows_resolved_member() -> None:
    result = MagicMock()
    result.scalar.return_value = True
    session = AsyncMock()
    session.execute.return_value = result
    service = ProjectAuthorizationService(session)

    await service.authorize_memory_scope(
        user_id=uuid4(), scope_type=MemoryScopeType.PROJECT, project_id=uuid4()
    )

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_project_scope_hides_non_member_project() -> None:
    result = MagicMock()
    result.scalar.return_value = False
    session = AsyncMock()
    session.execute.return_value = result
    service = ProjectAuthorizationService(session)

    with pytest.raises(ForbiddenException):
        await service.authorize_memory_scope(
            user_id=uuid4(), scope_type=MemoryScopeType.PROJECT, project_id=uuid4()
        )


@pytest.mark.asyncio
async def test_scope_shape_is_validated_before_query() -> None:
    session = AsyncMock()
    service = ProjectAuthorizationService(session)

    with pytest.raises(ValidationException):
        await service.authorize_memory_scope(
            user_id=uuid4(), scope_type=MemoryScopeType.PROJECT, project_id=None
        )
    with pytest.raises(ValidationException):
        await service.authorize_memory_scope(
            user_id=uuid4(), scope_type=MemoryScopeType.PERSONAL, project_id=uuid4()
        )

    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorize_project_access_allows_resolved_member() -> None:
    result = MagicMock()
    result.scalar.return_value = True
    session = AsyncMock()
    session.execute.return_value = result
    service = ProjectAuthorizationService(session)

    await service.authorize_project_access(user_id=uuid4(), project_id=uuid4())

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_authorize_project_access_hides_non_member_project() -> None:
    result = MagicMock()
    result.scalar.return_value = False
    session = AsyncMock()
    session.execute.return_value = result
    service = ProjectAuthorizationService(session)

    with pytest.raises(ForbiddenException):
        await service.authorize_project_access(user_id=uuid4(), project_id=uuid4())
