from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.types import ResearchRunDispatchStatus
from app.models.research_run_dispatch import ResearchRunDispatch
from app.repositories.research_run_dispatch import ResearchRunDispatchRepository


@pytest.mark.asyncio
async def test_reopen_flips_a_completed_dispatch_back_to_pending() -> None:
    run_id = uuid4()
    dispatch = ResearchRunDispatch(
        run_id=run_id,
        status=ResearchRunDispatchStatus.COMPLETED.value,
    )
    session = AsyncMock()
    session.get.return_value = dispatch
    repository = ResearchRunDispatchRepository(session)

    await repository.reopen(run_id=run_id)

    assert dispatch.status == ResearchRunDispatchStatus.PENDING.value
    assert dispatch.lease_expires_at is None
    assert dispatch.completed_at is None
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_reopen_raises_for_an_unknown_run() -> None:
    session = AsyncMock()
    session.get.return_value = None
    repository = ResearchRunDispatchRepository(session)

    with pytest.raises(RuntimeError, match="was not found"):
        await repository.reopen(run_id=uuid4())
