from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from app.repositories.generation_usage import GenerationUsageRepository


@pytest.mark.asyncio
async def test_sum_for_conversation_rolls_up_cost_requests_and_tokens() -> None:
    conversation_id = uuid4()
    owner_id = uuid4()

    session = AsyncMock()
    execute_result = MagicMock()
    execute_result.one.return_value = (Decimal("1.23456789"), 4, 9000)
    session.execute = AsyncMock(return_value=execute_result)

    repository = GenerationUsageRepository(session)

    summary = await repository.sum_for_conversation(conversation_id, owner_id)

    session.execute.assert_awaited_once()
    assert summary == {
        "conversation_id": conversation_id,
        "total_cost_usd": pytest.approx(1.23456789),
        "total_requests": 4,
        "total_tokens": 9000,
    }
