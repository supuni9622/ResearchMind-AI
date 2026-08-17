"""
Integration test for GET /memory/context.

Covers a real gap found while auditing owner-scoping: `MemoryContextResponse`
was missing `user_memories` entirely, so the read-side fix in
`MemoryService.get_context()` (see `docs/todo/user-memory-profile-injection-gap.md`)
never reached this direct API view of the assembled context, even though it
already reached the prompt-injection path used by Chat/Research.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.memory.create import get_memory_metrics
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.models import MemoryContext, MemoryRecord
from app.ai.memory.observability.metrics import (
    MEMORY_MUTATION_ACCEPTED,
    MEMORY_MUTATION_REJECTED,
)
from app.api.v1.memory import _check_memory_mutation_rate_limit
from app.auth.dependencies import get_current_user
from app.dependencies.memory import get_memory_governance_service, get_memory_service
from app.dependencies.project import get_project_authorization_service
from app.dependencies.rate_limiting import get_rate_limiter
from app.exceptions.base import ForbiddenException
from app.infrastructure.metrics.interfaces import MetricsRecorder
from app.infrastructure.rate_limiting import RateLimitResult
from app.main import app
from app.models.user import User
from fastapi.testclient import TestClient

_OWNER_ID = uuid.uuid4()


def _record(memory_type: MemoryType, content: str) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid.uuid4(),
        owner_id=_OWNER_ID,
        type=memory_type,
        content=content,
        importance_score=0.8,
        created_at=now,
        updated_at=now,
    )


class _FakeMemoryService:
    def __init__(self) -> None:
        self.mutation_calls: list[str] = []
        self.list_kwargs: dict[str, object] = {}

    async def get_context(self, **_: object) -> MemoryContext:
        return MemoryContext(
            session_memories=[_record(MemoryType.SESSION, "discussed RAG pipelines")],
            user_memories=[_record(MemoryType.USER, "prefers concise answers")],
            semantic_memories=[],
            research_memories=[],
        )

    async def list_memories(self, **kwargs: object) -> tuple[list[MemoryRecord], int]:
        self.list_kwargs = kwargs
        return [_record(MemoryType.USER, "prefers concise answers")], 1

    async def get_scope_settings(self, **_: object) -> tuple[bool, bool, bool]:
        return True, True, True

    async def update_scope_settings(self, **kwargs: object) -> tuple[bool, bool, bool]:
        return (
            bool(kwargs["capture_enabled"]),
            bool(kwargs["retrieval_enabled"]),
            bool(kwargs["inherit_personal_memory"]),
        )

    async def move_memory(self, **kwargs: object) -> MemoryRecord:
        self.mutation_calls.append("move")
        return _record(MemoryType.USER, "prefers concise answers")

    async def remember(self, **kwargs: object) -> MemoryRecord:
        self.mutation_calls.append("create")
        return _record(kwargs["type"], str(kwargs["content"]))  # type: ignore[arg-type]

    async def update_memory(self, **kwargs: object) -> MemoryRecord:
        self.mutation_calls.append("update")
        return _record(MemoryType.USER, str(kwargs["content"]))

    async def forget(self, **_: object) -> bool:
        self.mutation_calls.append("delete")
        return True


class _FakeRateLimiter:
    def __init__(self) -> None:
        self.decisions: list[RateLimitResult] = []
        self.keys: list[str] = []

    async def check(self, *, key: str, **_: object) -> RateLimitResult:
        self.keys.append(key)
        if self.decisions:
            return self.decisions.pop(0)
        return RateLimitResult(allowed=True, retry_after_seconds=0)


class _FakeProjectAuthorization:
    def __init__(self) -> None:
        self.allowed = True
        self.calls: list[dict[str, object]] = []

    async def authorize_memory_scope(self, **kwargs: object) -> None:
        self.calls.append(kwargs)
        if not self.allowed:
            raise ForbiddenException(message="Project memory access is not permitted.")

    async def list_accessible_projects(self, **_: object) -> list[tuple[object, str]]:
        return []


class _FakeGovernanceService:
    async def export_scope(self, **_: object) -> list[MemoryRecord]:
        return [_record(MemoryType.USER, "portable preference")]

    async def preview_deletion(self, **kwargs: object) -> tuple[str, object]:
        ids = kwargs["memory_ids"]
        return "x" * 32, SimpleNamespace(
            expected_count=len(ids) if isinstance(ids, list) else 3,
            expires_at=datetime.now(UTC),
        )

    async def execute_deletion(self, **_: object) -> object:
        return self._job()

    async def get_job(self, **_: object) -> object:
        return self._job()

    async def retry(self, **_: object) -> object:
        return self._job()

    @staticmethod
    def _job() -> object:
        return SimpleNamespace(
            id=uuid.uuid4(),
            scope_type="personal",
            project_id=None,
            status="completed",
            requested_count=1,
            deleted_postgres=1,
            deleted_qdrant=0,
            deleted_valkey=2,
            deleted_artifacts=0,
            failure_stage=None,
            completed_at=datetime.now(UTC),
        )


def _fake_user() -> User:
    return User(
        id=_OWNER_ID,
        auth_provider="test",
        provider_user_id=str(_OWNER_ID),
        email=f"{_OWNER_ID}@example.com",
    )


@pytest.fixture
def fake_memory_service() -> Iterator[_FakeMemoryService]:
    service = _FakeMemoryService()
    limiter = _FakeRateLimiter()
    metrics = MagicMock(spec=MetricsRecorder)
    project_authorization = _FakeProjectAuthorization()
    governance = _FakeGovernanceService()
    app.dependency_overrides[get_memory_service] = lambda: service
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_memory_metrics] = lambda: metrics
    app.dependency_overrides[get_project_authorization_service] = lambda: project_authorization
    app.dependency_overrides[get_memory_governance_service] = lambda: governance
    service.rate_limiter = limiter  # type: ignore[attr-defined]
    service.metrics = metrics  # type: ignore[attr-defined]
    service.project_authorization = project_authorization  # type: ignore[attr-defined]

    yield service

    app.dependency_overrides.pop(get_memory_service, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_rate_limiter, None)
    app.dependency_overrides.pop(get_memory_metrics, None)
    app.dependency_overrides.pop(get_project_authorization_service, None)
    app.dependency_overrides.pop(get_memory_governance_service, None)


def test_context_response_includes_user_memories(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    response = client.get(
        "/api/v1/memory/context",
        params={"session_id": str(uuid.uuid4())},
    )

    assert response.status_code == 200
    body = response.json()
    assert [m["content"] for m in body["user_memories"]] == ["prefers concise answers"]
    assert [m["content"] for m in body["session_memories"]] == ["discussed RAG pipelines"]


def test_list_response_contains_only_owner_scoped_user_memories(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    response = client.get(
        "/api/v1/memory",
        params={"search": "concise", "source": "feedback", "limit": 10, "offset": 20},
    )

    assert response.status_code == 200
    assert [memory["content"] for memory in response.json()["memories"]] == [
        "prefers concise answers"
    ]
    assert response.json() | {"memories": []} == {
        "memories": [],
        "total": 1,
        "limit": 10,
        "offset": 20,
    }
    assert fake_memory_service.list_kwargs == {
        "owner_id": _OWNER_ID,
        "memory_types": None,
        "scope_type": MemoryScopeType.PERSONAL,
        "project_id": None,
        "search": "concise",
        "source": "feedback",
        "created_from": None,
        "created_to": None,
        "updated_from": None,
        "updated_to": None,
        "origin": None,
        "limit": 10,
        "offset": 20,
    }
    listed = response.json()["memories"][0]
    assert "owner_id" not in listed
    assert "metadata" not in listed
    assert listed["editable"] is True
    assert listed["origin"] == "inferred"


def test_create_and_update_share_write_bucket_but_delete_is_separate(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    memory_id = uuid.uuid4()
    create = client.post(
        "/api/v1/memory",
        json={"type": "user", "content": "Prefer concise answers"},
    )
    update = client.put(
        f"/api/v1/memory/{memory_id}",
        json={"type": "user", "content": "Prefer detailed answers"},
    )
    delete = client.delete(f"/api/v1/memory/{memory_id}")

    assert create.status_code == 200
    assert update.status_code == 200
    assert delete.status_code == 400
    assert "confirmation token" in delete.text
    assert fake_memory_service.mutation_calls == ["create", "update"]
    limiter = fake_memory_service.rate_limiter  # type: ignore[attr-defined]
    assert limiter.keys == [
        f"memory_write:{_OWNER_ID}",
        f"memory_write:{_OWNER_ID}",
        f"memory_delete:{_OWNER_ID}",
    ]
    metrics = fake_memory_service.metrics  # type: ignore[attr-defined]
    assert metrics.increment.call_count == 3
    metrics.increment.assert_any_call(
        metric=MEMORY_MUTATION_ACCEPTED,
        labels={"operation": "create"},
    )


def test_rate_limited_create_returns_429_before_storage(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    limiter = fake_memory_service.rate_limiter  # type: ignore[attr-defined]
    limiter.decisions.append(RateLimitResult(allowed=False, retry_after_seconds=17))

    response = client.post(
        "/api/v1/memory",
        json={"type": "user", "content": "Prefer concise answers"},
    )

    assert response.status_code == 429
    assert response.headers["retry-after"] == "17"
    assert fake_memory_service.mutation_calls == []
    metrics = fake_memory_service.metrics  # type: ignore[attr-defined]
    metrics.increment.assert_called_once_with(
        metric=MEMORY_MUTATION_REJECTED,
        labels={"operation": "create"},
    )


def test_memory_reads_do_not_consume_mutation_buckets(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    response = client.get(
        "/api/v1/memory/context",
        params={"session_id": str(uuid.uuid4())},
    )

    assert response.status_code == 200
    limiter = fake_memory_service.rate_limiter  # type: ignore[attr-defined]
    assert limiter.keys == []


def test_project_authorization_precedes_memory_listing(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    project_id = uuid.uuid4()
    authorization = fake_memory_service.project_authorization  # type: ignore[attr-defined]
    authorization.allowed = False

    response = client.get(
        "/api/v1/memory",
        params={"scope_type": "project", "project_id": str(project_id)},
    )

    assert response.status_code == 403
    assert fake_memory_service.list_kwargs == {}
    assert authorization.calls == [
        {
            "user_id": _OWNER_ID,
            "scope_type": MemoryScopeType.PROJECT,
            "project_id": project_id,
        }
    ]


def test_list_forwards_scope_type_date_and_origin_filters(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    project_id = uuid.uuid4()
    response = client.get(
        "/api/v1/memory",
        params=[
            ("scope_type", "project"),
            ("project_id", str(project_id)),
            ("type", "semantic"),
            ("type", "research"),
            ("created_from", "2026-01-01T00:00:00Z"),
            ("updated_to", "2026-12-31T00:00:00Z"),
            ("origin", "explicit"),
        ],
    )

    assert response.status_code == 200
    assert fake_memory_service.list_kwargs["memory_types"] == [
        MemoryType.SEMANTIC,
        MemoryType.RESEARCH,
    ]
    assert fake_memory_service.list_kwargs["scope_type"] == MemoryScopeType.PROJECT
    assert fake_memory_service.list_kwargs["project_id"] == project_id
    assert fake_memory_service.list_kwargs["origin"] == "explicit"


def test_move_authorizes_source_and_destination_before_mutation(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    memory_id = uuid.uuid4()
    project_id = uuid.uuid4()
    response = client.post(
        f"/api/v1/memory/{memory_id}/move",
        json={
            "source_scope_type": "personal",
            "source_project_id": None,
            "scope_type": "project",
            "project_id": str(project_id),
            "confirmed": True,
        },
    )

    assert response.status_code == 200
    authorization = fake_memory_service.project_authorization  # type: ignore[attr-defined]
    assert authorization.calls[-2:] == [
        {
            "user_id": _OWNER_ID,
            "scope_type": MemoryScopeType.PERSONAL,
            "project_id": None,
        },
        {
            "user_id": _OWNER_ID,
            "scope_type": MemoryScopeType.PROJECT,
            "project_id": project_id,
        },
    ]
    assert fake_memory_service.mutation_calls[-1] == "move"


def test_move_requires_confirmation_before_authorization_or_storage(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    response = client.post(
        f"/api/v1/memory/{uuid.uuid4()}/move",
        json={
            "source_scope_type": "personal",
            "scope_type": "project",
            "project_id": str(uuid.uuid4()),
            "confirmed": False,
        },
    )

    assert response.status_code == 400
    assert "move" not in fake_memory_service.mutation_calls


def test_scope_settings_state_retention_is_explicit(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
) -> None:
    update = client.put(
        "/api/v1/memory/settings",
        json={
            "scope_type": "personal",
            "project_id": None,
            "capture_enabled": False,
            "retrieval_enabled": False,
        },
    )

    assert update.status_code == 200
    assert update.json() == {
        "scope_type": "personal",
        "project_id": None,
        "capture_enabled": False,
        "retrieval_enabled": False,
        "inherit_personal_memory": True,
        "retention_enabled": True,
    }


def test_memory_projects_are_listed_from_authorized_boundary(
    client: TestClient, fake_memory_service: _FakeMemoryService
) -> None:
    response = client.get("/api/v1/memory/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_portable_export_excludes_owner_and_internal_metadata(
    client: TestClient, fake_memory_service: _FakeMemoryService
) -> None:
    response = client.get("/api/v1/memory/export")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "researchmind.memory.export.v1"
    assert body["memories"][0]["content"] == "portable preference"
    assert "owner_id" not in body["memories"][0]
    assert "metadata" not in body["memories"][0]


def test_deletion_requires_server_preview_then_accepts_token(
    client: TestClient, fake_memory_service: _FakeMemoryService
) -> None:
    memory_id = uuid.uuid4()
    preview = client.post(
        "/api/v1/memory/deletion/preview",
        json={"scope_type": "personal", "memory_ids": [str(memory_id)]},
    )
    assert preview.status_code == 200
    assert preview.json()["affected_count"] == 1
    assert preview.json()["immediate_erasure"] is True

    execute = client.post(
        "/api/v1/memory/deletion/jobs",
        json={"confirmation_token": preview.json()["confirmation_token"]},
    )
    assert execute.status_code == 200
    assert execute.json()["status"] == "completed"
    assert execute.json()["deleted_postgres"] == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"type": "user", "content": "x" * 10_001},
        {"type": "user", "content": "valid", "metadata": {"x": "y" * 17_000}},
        {
            "type": "user",
            "content": "valid",
            "metadata": {"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}},
        },
    ],
)
def test_oversized_or_deep_memory_payload_is_rejected_before_storage(
    client: TestClient,
    fake_memory_service: _FakeMemoryService,
    payload: dict[str, object],
) -> None:
    response = client.post("/api/v1/memory", json=payload)

    assert response.status_code == 422
    assert fake_memory_service.mutation_calls == []


@pytest.mark.asyncio
async def test_public_mutation_limiter_failure_is_fail_closed() -> None:
    limiter = MagicMock()
    limiter.check = AsyncMock(side_effect=RuntimeError("valkey unavailable"))
    metrics = MagicMock(spec=MetricsRecorder)

    with pytest.raises(RuntimeError, match="valkey unavailable"):
        await _check_memory_mutation_rate_limit(
            rate_limiter=limiter,
            metrics=metrics,
            owner_id=_OWNER_ID,
            operation="create",
        )
