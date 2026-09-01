from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.ai.memory.storage.valkey_store import ValkeySessionStore
from app.ai.memory.storage.vector_index import MemoryVectorIndex


def test_valkey_keys_separate_personal_and_project_scopes() -> None:
    owner_id = uuid4()
    memory_id = uuid4()
    project_a = uuid4()
    project_b = uuid4()

    personal = ValkeySessionStore._record_key(owner_id, MemoryScopeType.PERSONAL, None, memory_id)
    scoped_a = ValkeySessionStore._record_key(
        owner_id, MemoryScopeType.PROJECT, project_a, memory_id
    )
    scoped_b = ValkeySessionStore._record_key(
        owner_id, MemoryScopeType.PROJECT, project_b, memory_id
    )

    assert len({personal, scoped_a, scoped_b}) == 3
    assert f"project:{project_a}" in scoped_a
    assert f"project:{project_b}" in scoped_b


def test_valkey_global_key_does_not_collide_with_personal_or_produce_project_none() -> None:
    """Regression: a binary `"personal" if PERSONAL else f"project:{project_id}"`
    ternary would silently produce the broken segment "project:None" for a
    GLOBAL scope (project_id is also None for GLOBAL)."""

    owner_id = uuid4()
    memory_id = uuid4()

    personal = ValkeySessionStore._record_key(owner_id, MemoryScopeType.PERSONAL, None, memory_id)
    glob = ValkeySessionStore._record_key(owner_id, MemoryScopeType.GLOBAL, None, memory_id)

    assert personal != glob
    assert "project:None" not in glob
    assert "global" in glob


@pytest.mark.asyncio
async def test_qdrant_project_search_requires_exact_scope_and_project() -> None:
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.query_points.return_value = SimpleNamespace(points=[])
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)
    owner_id = uuid4()
    project_id = uuid4()

    await index.search(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
        vector=[0.1, 0.2, 0.3],
        memory_types=[MemoryType.RESEARCH],
        top_k=5,
    )

    query_filter = client.query_points.await_args.kwargs["query_filter"]
    encoded = query_filter.model_dump()
    assert str(owner_id) in str(encoded)
    assert MemoryScopeType.PROJECT.value in str(encoded)
    assert str(project_id) in str(encoded)


@pytest.mark.asyncio
async def test_qdrant_global_search_requires_exact_scope_no_project() -> None:
    """Regression for the real bug found while adding GLOBAL: the old
    filter code was `if PROJECT: ... else: personal-or-null`, so a naive
    GLOBAL addition would have silently fallen into that `else` and been
    treated as PERSONAL. GLOBAL must get its own `must`-clause exact match
    on scope_type, with no project_id condition and no `should` fallback."""

    client = AsyncMock()
    client.collection_exists.return_value = True
    client.query_points.return_value = SimpleNamespace(points=[])
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)
    owner_id = uuid4()

    await index.search(
        owner_id=owner_id,
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
        vector=[0.1, 0.2, 0.3],
        memory_types=[MemoryType.SEMANTIC],
        top_k=5,
    )

    query_filter = client.query_points.await_args.kwargs["query_filter"]
    assert query_filter.should is None
    encoded = str(query_filter.model_dump())
    assert MemoryScopeType.GLOBAL.value in encoded
    assert MemoryScopeType.PERSONAL.value not in encoded


@pytest.mark.asyncio
async def test_qdrant_global_and_personal_filters_are_not_the_same() -> None:
    client = AsyncMock()
    client.collection_exists.return_value = True
    client.query_points.return_value = SimpleNamespace(points=[])
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)
    owner_id = uuid4()

    await index.search(
        owner_id=owner_id,
        scope_type=MemoryScopeType.GLOBAL,
        project_id=None,
        vector=[0.1, 0.2, 0.3],
        memory_types=[MemoryType.SEMANTIC],
        top_k=5,
    )
    global_filter = client.query_points.await_args.kwargs["query_filter"].model_dump()

    await index.search(
        owner_id=owner_id,
        scope_type=MemoryScopeType.PERSONAL,
        project_id=None,
        vector=[0.1, 0.2, 0.3],
        memory_types=[MemoryType.SEMANTIC],
        top_k=5,
    )
    personal_filter = client.query_points.await_args.kwargs["query_filter"].model_dump()

    assert global_filter != personal_filter


@pytest.mark.asyncio
async def test_qdrant_payload_persists_scope() -> None:
    client = AsyncMock()
    client.collection_exists.return_value = True
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)
    project_id = uuid4()

    await index.upsert(
        memory_id=uuid4(),
        owner_id=uuid4(),
        memory_type=MemoryType.SEMANTIC,
        scope_type=MemoryScopeType.PROJECT,
        project_id=project_id,
        vector=[0.1, 0.2, 0.3],
    )

    point = client.upsert.await_args.kwargs["points"][0]
    assert point.payload["scope_type"] == "project"
    assert point.payload["project_id"] == str(project_id)
