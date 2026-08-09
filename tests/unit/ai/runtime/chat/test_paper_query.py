from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.chat.paper_query import PaperQueryExtractionResult, PaperQueryExtractionService
from app.ai.runtime.generation.enums import GenerationProvider


@pytest.mark.asyncio
async def test_uses_the_cheap_provider_when_configured() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PaperQueryExtractionResult(query="retrieval augmented generation"),
    )
    service = PaperQueryExtractionService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    query = await service.extract(
        user_prompt="can I have research papers about retrieval augmented generation?",
        owner_id=uuid4(),
        session_id=uuid4(),
    )

    assert query == "retrieval augmented generation"
    runtime.execute.assert_awaited_once()
    assert runtime.execute.await_args.kwargs["provider"] == GenerationProvider.OPENAI


@pytest.mark.asyncio
async def test_falls_back_to_the_shared_runtime_when_no_cheap_provider_configured() -> None:
    cheap_runtime = AsyncMock()
    fallback_runtime = AsyncMock()
    fallback_runtime.execute.return_value = SimpleNamespace(
        parsed_output=PaperQueryExtractionResult(query="earthquake mechanisms"),
    )
    service = PaperQueryExtractionService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=None,
        fallback_generation_runtime=fallback_runtime,
    )

    query = await service.extract(
        user_prompt="why do earthquakes happen", owner_id=uuid4(), session_id=uuid4()
    )

    assert query == "earthquake mechanisms"
    cheap_runtime.execute.assert_not_awaited()
    fallback_runtime.execute.assert_awaited_once()
    assert fallback_runtime.execute.await_args.kwargs["provider"] is None


@pytest.mark.asyncio
async def test_falls_back_to_shared_runtime_when_preferred_provider_fails() -> None:
    cheap_runtime = AsyncMock()
    cheap_runtime.execute.side_effect = RuntimeError("quota exhausted")
    fallback_runtime = AsyncMock()
    fallback_runtime.execute.return_value = SimpleNamespace(
        parsed_output=PaperQueryExtractionResult(query="large language models"),
    )
    service = PaperQueryExtractionService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=GenerationProvider.OPENAI,
        fallback_generation_runtime=fallback_runtime,
    )

    query = await service.extract(
        user_prompt="find papers about large language models",
        owner_id=uuid4(),
        session_id=uuid4(),
    )

    assert query == "large language models"
    fallback_runtime.execute.assert_awaited_once()
    fallback_request = fallback_runtime.execute.await_args.args[0]
    assert fallback_request.routing_strategy.value == "classification"
    assert fallback_runtime.execute.await_args.kwargs["provider"] is None


@pytest.mark.asyncio
async def test_model_failure_falls_back_to_the_raw_truncated_prompt() -> None:
    """Best-effort, matches `WebSearchNecessityService`'s fail-closed
    behavior -- the query extraction step must never break a chat turn."""

    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = PaperQueryExtractionService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    query = await service.extract(
        user_prompt="retrieval augmented generation", owner_id=uuid4(), session_id=uuid4()
    )

    assert query == "retrieval augmented generation"


@pytest.mark.asyncio
async def test_conversation_context_is_folded_into_the_extraction_prompt() -> None:
    """Regression coverage for the production bug (2026-07-26): a topicless
    follow-up like "find me some research articles in this field" has no
    resolvable subject without the turns that came before it. When
    `conversation_context` is supplied, it must reach the generation
    request so the model can resolve the reference."""

    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=PaperQueryExtractionResult(query="earthquake mechanisms"),
    )
    service = PaperQueryExtractionService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    query = await service.extract(
        user_prompt="find me some research articles in this field",
        owner_id=uuid4(),
        session_id=uuid4(),
        conversation_context="User: why do earthquakes happen\nAssistant: ...",
    )

    assert query == "earthquake mechanisms"
    sent_prompt = runtime.execute.await_args.args[0].user_prompt
    assert "Conversation so far" in sent_prompt
    assert "why do earthquakes happen" in sent_prompt
    assert "find me some research articles in this field" in sent_prompt


@pytest.mark.asyncio
async def test_schema_invalid_output_falls_back_to_the_raw_prompt() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output="not a schema object")
    service = PaperQueryExtractionService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    query = await service.extract(
        user_prompt="tell me about earthquakes", owner_id=uuid4(), session_id=uuid4()
    )

    assert query == "tell me about earthquakes"
