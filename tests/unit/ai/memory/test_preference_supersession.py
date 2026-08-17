from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryRecord
from app.ai.memory.policy.models import (
    PreferenceKind,
    PreferenceSupersessionDecision,
    PreferenceTopicClassification,
    PreferenceValueType,
)
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

    assert result is not None
    assert result.record is existing[1]
    assert result.reason == "same topic"


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

    assert result is not None
    assert result.record is existing[0]
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

    assert result is not None
    assert result.record is existing[0]


@pytest.mark.asyncio
async def test_classifies_stable_topic_for_dormant_preference_lookup() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PreferenceTopicClassification(
            preference_key="Response Length",
            preference_kind=PreferenceKind.RESPONSE_LENGTH,
            normalized_value=" Detailed ",
            value_type=PreferenceValueType.STRING,
            confidence=0.96,
            explicit=True,
            search_terms=[" Answers ", "response length"],
        )
    )
    service = PreferenceSupersessionService(runtime, provider=GenerationProvider.OPENAI)

    topic = await service.classify_topic(
        owner_id=uuid4(), new_content="I now prefer detailed answers"
    )

    assert topic is not None
    assert topic.preference_key == "response_length"
    assert topic.normalized_value == "Detailed"
    assert topic.search_terms == ["answers", "response length"]


def test_deterministic_match_requires_one_high_confidence_explicit_controlled_key() -> None:
    existing = _record("prefers concise answers").model_copy(
        update={
            "metadata": {
                "preference": {
                    "schema_version": "v1",
                    "key": "response_length",
                }
            }
        }
    )
    classification = PreferenceTopicClassification(
        preference_key="response_length",
        preference_kind=PreferenceKind.RESPONSE_LENGTH,
        normalized_value="detailed",
        value_type=PreferenceValueType.STRING,
        confidence=0.95,
        explicit=True,
        search_terms=["answers"],
    )

    match = PreferenceSupersessionService.find_deterministic_superseded(
        classification=classification,
        existing=[existing],
        confidence_threshold=0.85,
    )

    assert match is not None
    assert match.record is existing
    assert match.reason == "deterministic_typed_preference_key_match"


@pytest.mark.parametrize(
    ("kind", "confidence", "explicit"),
    [
        (PreferenceKind.CUSTOM, 0.99, True),
        (PreferenceKind.RESPONSE_LENGTH, 0.5, True),
        (PreferenceKind.RESPONSE_LENGTH, 0.99, False),
    ],
)
def test_deterministic_match_rejects_custom_uncertain_or_inferred_preferences(
    kind: PreferenceKind,
    confidence: float,
    explicit: bool,
) -> None:
    existing = _record("prefers concise answers").model_copy(
        update={"metadata": {"preference": {"schema_version": "v1", "key": "response_length"}}}
    )
    classification = PreferenceTopicClassification(
        preference_key="response_length",
        preference_kind=kind,
        normalized_value="detailed",
        value_type=PreferenceValueType.STRING,
        confidence=confidence,
        explicit=explicit,
        search_terms=["answers"],
    )

    assert (
        PreferenceSupersessionService.find_deterministic_superseded(
            classification=classification,
            existing=[existing],
            confidence_threshold=0.85,
        )
        is None
    )


@pytest.mark.asyncio
async def test_topic_classification_failure_fails_open() -> None:
    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = PreferenceSupersessionService(runtime, provider=GenerationProvider.OPENAI)

    assert await service.classify_topic(owner_id=uuid4(), new_content="prefers dark mode") is None
