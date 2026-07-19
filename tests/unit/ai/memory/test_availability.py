from unittest.mock import AsyncMock
from uuid import uuid4

from app.ai.memory.retrieval.availability import DurableMemoryAvailabilityService


async def test_availability_cache_and_owner_scoped_store_check() -> None:
    store = AsyncMock()
    store.exists_for_owner = AsyncMock(return_value=False)
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    service = DurableMemoryAvailabilityService(store, redis)

    assert await service.has_durable_memory(owner_id=uuid4()) is False
    store.exists_for_owner.assert_awaited_once()
    redis.set.assert_awaited_once()


async def test_availability_store_failure_fails_open() -> None:
    store = AsyncMock()
    store.exists_for_owner = AsyncMock(side_effect=RuntimeError("postgres unavailable"))
    service = DurableMemoryAvailabilityService(store)

    assert await service.has_durable_memory(owner_id=uuid4()) is True
