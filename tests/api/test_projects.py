"""Route-wiring tests for /api/v1/projects -- status codes, schema shape,
and exception propagation, using a fake `ProjectService` (real business
logic and authorization are covered separately by
tests/integration/test_project.py's real-DB tests). Mirrors the
dependency_overrides + fake-service pattern in tests/api/test_memory.py."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app.auth.dependencies import get_current_user
from app.dependencies.project import get_project_service
from app.exceptions.base import ForbiddenException, NotFoundException
from app.main import app
from app.models.project import Project
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_ID = uuid.uuid4()


def _fake_user() -> User:
    return User(
        id=_OWNER_ID,
        auth_provider="test",
        provider_user_id=str(_OWNER_ID),
        email=f"{_OWNER_ID}@example.com",
    )


def _project(name: str = "Alpha", description: str | None = "First project") -> Project:
    now = datetime.now(UTC)
    return Project(
        id=uuid.uuid4(),
        owner_id=_OWNER_ID,
        name=name,
        description=description,
        created_at=now,
        updated_at=now,
    )


class _FakeProjectService:
    def __init__(self) -> None:
        self.created: dict[str, object] | None = None
        self.updated: dict[str, object] | None = None
        self.deleted: uuid.UUID | None = None
        self.raise_on_get: Exception | None = None
        self.raise_on_update: Exception | None = None
        self.raise_on_delete: Exception | None = None
        self._project = _project()

    async def create(self, *, owner_id: uuid.UUID, name: str, description: str | None) -> Project:
        self.created = {"owner_id": owner_id, "name": name, "description": description}
        self._project = _project(name=name, description=description)
        return self._project

    async def list_for_user(self, *, user_id: uuid.UUID) -> list[tuple[Project, str]]:
        return [(self._project, "owner")]

    async def get_for_user(self, *, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        if self.raise_on_get is not None:
            raise self.raise_on_get
        return self._project

    async def update(
        self,
        *,
        owner_id: uuid.UUID,
        project_id: uuid.UUID,
        name: str | None,
        description: str | None,
    ) -> Project:
        if self.raise_on_update is not None:
            raise self.raise_on_update
        self.updated = {"project_id": project_id, "name": name, "description": description}
        return self._project

    async def delete(self, *, owner_id: uuid.UUID, project_id: uuid.UUID) -> None:
        if self.raise_on_delete is not None:
            raise self.raise_on_delete
        self.deleted = project_id


@pytest.fixture
def fake_project_service() -> Iterator[_FakeProjectService]:
    service = _FakeProjectService()
    app.dependency_overrides[get_project_service] = lambda: service
    app.dependency_overrides[get_current_user] = _fake_user

    yield service

    app.dependency_overrides.pop(get_project_service, None)
    app.dependency_overrides.pop(get_current_user, None)


def test_create_project_returns_201_with_owner_role(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    response = client.post(
        "/api/v1/projects", json={"name": "Alpha", "description": "First project"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alpha"
    assert body["role"] == "owner"
    assert fake_project_service.created == {
        "owner_id": _OWNER_ID,
        "name": "Alpha",
        "description": "First project",
    }


def test_list_projects_returns_accessible_projects(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    response = client.get("/api/v1/projects")

    assert response.status_code == 200
    body = response.json()
    assert len(body["projects"]) == 1
    assert body["projects"][0]["role"] == "owner"


def test_get_project_returns_403_for_non_member(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    fake_project_service.raise_on_get = ForbiddenException(
        message="Project access is not permitted."
    )

    response = client.get(f"/api/v1/projects/{uuid.uuid4()}")

    assert response.status_code == 403


def test_get_project_returns_404_when_missing(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    fake_project_service.raise_on_get = NotFoundException(message="Project was not found.")

    response = client.get(f"/api/v1/projects/{uuid.uuid4()}")

    assert response.status_code == 404


def test_update_project_returns_403_for_non_owner_member(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    fake_project_service.raise_on_update = ForbiddenException(
        message="Only the project owner can do this."
    )

    response = client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"name": "Hijacked"})

    assert response.status_code == 403


def test_delete_project_returns_204(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    project_id = uuid.uuid4()

    response = client.delete(f"/api/v1/projects/{project_id}")

    assert response.status_code == 204
    assert fake_project_service.deleted == project_id


def test_create_project_rejects_empty_name(
    client: TestClient, fake_project_service: _FakeProjectService
) -> None:
    response = client.post("/api/v1/projects", json={"name": ""})

    assert response.status_code == 422
