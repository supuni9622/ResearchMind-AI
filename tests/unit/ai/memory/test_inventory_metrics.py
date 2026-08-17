from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.memory.observability import metrics
from app.ai.memory.observability.inventory import MemoryInventoryMetricsService
from app.ai.memory.storage.vector_index import MemoryVectorIndex


@pytest.mark.asyncio
async def test_inventory_records_only_bounded_aggregate_labels() -> None:
    missing_id = uuid4()
    orphan_id = uuid4()
    shared_id = uuid4()
    repository = MagicMock(
        memory_observability_snapshot=AsyncMock(
            return_value={
                "counts": {("user", "personal"): 7},
                "oldest_age_seconds": {"user": 3600.0},
                "sizes": {"table": 100, "index": 50, "total": 150},
                "distributions": {("owner", "p95"): 4.0},
            }
        ),
        list_vector_memory_ids=AsyncMock(return_value={missing_id, shared_id}),
    )
    vector_index = MagicMock(list_point_ids=AsyncMock(return_value={shared_id, orphan_id}))
    recorder = MagicMock()

    await MemoryInventoryMetricsService(repository, vector_index, recorder).collect()

    calls = recorder.set_gauge.call_args_list
    assert any(
        call.kwargs
        == {
            "metric": metrics.STORAGE_ROWS,
            "value": 7.0,
            "labels": {"type": "user", "scope": "personal"},
        }
        for call in calls
    )
    drift = {
        call.kwargs["labels"]["kind"]: call.kwargs["value"]
        for call in calls
        if call.kwargs["metric"] == metrics.VECTOR_DRIFT
    }
    assert drift == {"missing_point": 1.0, "orphan_point": 1.0}
    assert all(
        "owner_id" not in (call.kwargs.get("labels") or {})
        and "project_id" not in (call.kwargs.get("labels") or {})
        for call in calls
    )


@pytest.mark.asyncio
async def test_vector_inventory_scrolls_every_page() -> None:
    first_id = uuid4()
    second_id = uuid4()
    client = MagicMock(
        collection_exists=AsyncMock(return_value=True),
        scroll=AsyncMock(
            side_effect=[
                ([SimpleNamespace(id=first_id)], "next"),
                ([SimpleNamespace(id=second_id)], None),
            ]
        ),
    )
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)

    assert await index.list_point_ids(batch_size=10) == {first_id, second_id}
    assert client.scroll.await_count == 2


@pytest.mark.asyncio
async def test_vector_inventory_does_not_create_a_missing_collection() -> None:
    client = MagicMock(collection_exists=AsyncMock(return_value=False), scroll=AsyncMock())
    index = MemoryVectorIndex(client, collection_name="memory", dimensions=3)

    assert await index.list_point_ids() == set()
    client.scroll.assert_not_awaited()
