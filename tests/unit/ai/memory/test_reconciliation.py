from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.observability.reconciliation import MemoryVectorReconciliationService


@pytest.mark.asyncio
async def test_reconciliation_removes_orphans_and_reindexes_missing_rows() -> None:
    missing_id = uuid4()
    orphan_id = uuid4()
    repository = AsyncMock()
    repository.list_vector_memory_ids.return_value = {missing_id}
    repository.list_by_ids_admin.return_value = [
        type(
            "Row",
            (),
            {
                "id": missing_id,
                "owner_id": uuid4(),
                "type": "semantic",
                "scope_type": "personal",
                "project_id": None,
                "content": "canonical fact",
            },
        )()
    ]
    vector_index = AsyncMock()
    vector_index.list_point_ids.return_value = {orphan_id}
    vector_index.delete.return_value = True
    vector_index.upsert.return_value = True
    embeddings = AsyncMock()
    embeddings.embed.return_value = [0.1, 0.2]

    result = await MemoryVectorReconciliationService(repository, vector_index, embeddings).repair()

    assert result == {
        "missing_found": 1,
        "orphaned_found": 1,
        "missing_repaired": 1,
        "orphaned_repaired": 1,
    }
    vector_index.delete.assert_awaited_once_with(orphan_id)
    vector_index.upsert.assert_awaited_once()
