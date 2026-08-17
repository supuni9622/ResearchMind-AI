from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.policy.models import PreferenceSupersessionDecision
from app.ai.memory.policy.supersession import PreferenceSupersessionService
from app.ai.runtime.generation.enums import GenerationProvider


def _record(content: str) -> MemoryRecord:
    now = datetime.now(UTC)
    return MemoryRecord(
        id=uuid4(),
        owner_id=uuid4(),
        type=MemoryType.USER,
        content=content,
        importance_score=0.8,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_returns_none_without_calling_the_model_when_there_is_nothing_to_compare() -> None:
    runtime = AsyncMock()
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers detail", existing=[]
    )

    assert result is None
    runtime.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_matched_index_returns_the_superseded_record() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PreferenceSupersessionDecision(superseded_index=2, reason="same topic"),
    )
    existing = [_record("prefers Claude"), _record("prefers concise answers")]
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers detailed answers", existing=existing
    )

    assert result is existing[1]


@pytest.mark.asyncio
async def test_zero_index_means_no_supersession() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PreferenceSupersessionDecision(superseded_index=0, reason="unrelated"),
    )
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers dark mode", existing=[_record("prefers Claude")]
    )

    assert result is None


@pytest.mark.asyncio
async def test_out_of_range_index_fails_closed_to_none() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PreferenceSupersessionDecision(superseded_index=99, reason="bad index"),
    )
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers dark mode", existing=[_record("prefers Claude")]
    )

    assert result is None


@pytest.mark.asyncio
async def test_generation_failure_falls_back_then_fails_closed_to_none() -> None:
    cheap_runtime = AsyncMock()
    cheap_runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = PreferenceSupersessionService(
        generation_runtime=cheap_runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers dark mode", existing=[_record("prefers Claude")]
    )

    assert result is None


@pytest.mark.asyncio
async def test_falls_back_to_the_fallback_provider_on_primary_failure() -> None:
    runtime = AsyncMock()
    runtime.execute.side_effect = [
        RuntimeError("primary down"),
        SimpleNamespace(
            parsed_output=PreferenceSupersessionDecision(superseded_index=1, reason="match")
        ),
    ]
    existing = [_record("prefers concise answers")]
    service = PreferenceSupersessionService(
        generation_runtime=runtime,
        provider=GenerationProvider.OPENAI,
        fallback_provider=GenerationProvider.GROQ,
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers detailed answers", existing=existing
    )

    assert result is existing[0]
    assert runtime.execute.await_count == 2


@pytest.mark.asyncio
async def test_schema_invalid_response_fails_closed_to_none() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output={"not": "the right shape"})
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers dark mode", existing=[_record("prefers Claude")]
    )

    assert result is None


@pytest.mark.asyncio
async def test_dict_parsed_output_is_coerced_into_the_model() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output={"superseded_index": 1, "reason": "same topic"}
    )
    existing = [_record("prefers concise answers")]
    service = PreferenceSupersessionService(
        generation_runtime=runtime, provider=GenerationProvider.OPENAI
    )

    result = await service.find_superseded(
        owner_id=uuid4(), new_content="prefers detailed answers", existing=existing
    )

    assert result is existing[0]
