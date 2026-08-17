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
from app.dependencies.memory import get_memory_service
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

    async def list_user_memories(self, **kwargs: object) -> tuple[list[MemoryRecord], int]:
        self.list_kwargs = kwargs
        return [_record(MemoryType.USER, "prefers concise answers")], 1

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
    app.dependency_overrides[get_memory_service] = lambda: service
    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_memory_metrics] = lambda: metrics
    app.dependency_overrides[get_project_authorization_service] = lambda: project_authorization
    service.rate_limiter = limiter  # type: ignore[attr-defined]
    service.metrics = metrics  # type: ignore[attr-defined]
    service.project_authorization = project_authorization  # type: ignore[attr-defined]

    yield service

    app.dependency_overrides.pop(get_memory_service, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_rate_limiter, None)
    app.dependency_overrides.pop(get_memory_metrics, None)
    app.dependency_overrides.pop(get_project_authorization_service, None)


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
        "scope_type": MemoryScopeType.PERSONAL,
        "project_id": None,
        "search": "concise",
        "source": "feedback",
        "limit": 10,
        "offset": 20,
    }


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
    assert delete.status_code == 204
    assert fake_memory_service.mutation_calls == ["create", "update", "delete"]
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
