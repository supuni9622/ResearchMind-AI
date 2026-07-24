from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.types import ResearchRunStatus
from app.models.research_run import ResearchRun
from app.repositories.research_run import ResearchRunRepository


@pytest.mark.asyncio
async def test_list_stale_awaiting_approval_queries_by_status_and_cutoff() -> None:
    stale_run = ResearchRun(
        id=uuid4(),
        owner_id=uuid4(),
        graph_thread_id=str(uuid4()),
        status=ResearchRunStatus.AWAITING_APPROVAL.value,
    )
    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [stale_run]
    session.execute = AsyncMock(return_value=execute_result)
    repository = ResearchRunRepository(session)
    cutoff = datetime.now(UTC)

    result = await repository.list_stale_awaiting_approval(older_than=cutoff)

    assert result == [stale_run]
    session.execute.assert_awaited_once()
