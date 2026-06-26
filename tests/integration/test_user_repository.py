import uuid

import pytest
from app.models.user import User
from app.repositories import UserRepository


@pytest.mark.asyncio
async def test_create_user(db_session):
    repository = UserRepository(db_session)

    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="john@example.com",
    )

    created = await repository.create(user)

    assert created.id is not None
    assert created.email == "john@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email(db_session):
    repository = UserRepository(db_session)

    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="alice@example.com",
    )

    await repository.create(user)

    result = await repository.get_by_email(
        "alice@example.com",
    )

    assert result is not None
    assert result.email == "alice@example.com"


@pytest.mark.asyncio
async def test_exists_by_email(db_session):
    repository = UserRepository(db_session)

    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="exists@example.com",
    )

    await repository.create(user)

    assert await repository.exists_by_email(
        "exists@example.com",
    )

    assert not await repository.exists_by_email(
        "missing@example.com",
    )


@pytest.mark.asyncio
async def test_delete_user(db_session):
    repository = UserRepository(db_session)

    user = User(
        auth_provider="cognito",
        provider_user_id=str(uuid.uuid4()),
        email="delete@example.com",
    )

    await repository.create(user)

    await repository.delete(user)

    result = await repository.get_by_email(
        "delete@example.com",
    )

    assert result is None
