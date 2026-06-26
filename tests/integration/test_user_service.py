import uuid

import pytest
from app.exceptions.base import ConflictException, NotFoundException
from app.services import UserService


@pytest.mark.asyncio
async def test_create_user(db_session):
    service = UserService(db_session)

    user = await service.create_user(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="service@example.com",
    )

    assert user.email == "service@example.com"


@pytest.mark.asyncio
async def test_duplicate_email_raises_conflict(db_session):
    service = UserService(db_session)

    await service.create_user(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="duplicate@example.com",
    )

    with pytest.raises(ConflictException):
        await service.create_user(
            auth_provider="cognito",
            provider_user_id=str(uuid.uuid4()),
            email="duplicate@example.com",
        )


@pytest.mark.asyncio
async def test_get_unknown_user_raises_not_found(db_session):
    service = UserService(db_session)

    with pytest.raises(NotFoundException):
        await service.get_user_by_email(
            "unknown@example.com",
        )


@pytest.mark.asyncio
async def test_sync_user_returns_existing_user(db_session):
    service = UserService(db_session)

    created = await service.create_user(
        auth_provider="cognito",
        provider_user_id="provider-123",
        email="sync@example.com",
    )

    synced = await service.sync_user(
        auth_provider="cognito",
        provider_user_id="provider-123",
        email="sync@example.com",
    )

    assert synced.id == created.id


@pytest.mark.asyncio
async def test_deactivate_user(db_session):
    service = UserService(db_session)

    user = await service.create_user(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="inactive@example.com",
    )

    updated = await service.deactivate_user(user)

    assert updated.is_active is False
