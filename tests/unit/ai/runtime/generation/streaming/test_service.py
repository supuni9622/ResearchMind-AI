"""
Unit tests for StreamingService.

Covers:
- Cache hit: replayed as synthetic START/TOKEN*/COMPLETE events without
  calling GenerationService.stream_generate() at all
- Cache miss: streams live from GenerationService.stream_generate(),
  converts each StreamChunk via the event adapter, and stores the
  assembled result once the stream completes
- A GenerationError raised mid-stream yields an ERROR event and never
  reaches CachingService.store()
- No CachingService wired: streams live with no cache lookup/store calls
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.events.create import get_event_adapter
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.generation.caching.enums import CacheLevel
from app.ai.runtime.generation.caching.models import CacheResult
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
    StreamChunk,
    StreamEventType,
)
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.streaming.service import StreamingService


def _make_request() -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt="hello",
        stream=True,
    )


def _make_result(content: str = "hello world") -> GenerationResult:
    return GenerationResult(
        request=_make_request(),
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="test-model",
        ),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content=content,
    )


def _make_registered_provider() -> MagicMock:
    provider = MagicMock()
    provider.provider = GenerationProvider.GROQ
    provider.config.model_name = "test-model"
    provider.count_tokens = AsyncMock(return_value=2)
    provider.estimate_cost = MagicMock(return_value=0.0)
    return provider


async def _fake_stream(chunks: list[StreamChunk]):
    for chunk in chunks:
        yield chunk


async def _collect(async_gen):
    return [item async for item in async_gen]


def _make_service(
    *,
    generation_service: MagicMock,
    provider: MagicMock,
    caching_service: AsyncMock | None,
    artifact_writer: AsyncMock | None = None,
) -> StreamingService:
    return StreamingService(
        generation_service=generation_service,
        registry=GenerationRegistry(providers=[provider]),
        event_adapter=get_event_adapter(),
        caching_service=caching_service,
        artifact_writer=artifact_writer,
    )


async def test_cache_hit_is_replayed_as_synthetic_events_without_live_streaming() -> None:
    provider = _make_registered_provider()

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock()

    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(
        return_value=CacheResult(
            hit=True,
            level=CacheLevel.EXACT,
            generation_result=_make_result("hello world"),
        )
    )

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert events[0].type == CoreEventType.START.value
    assert events[0].metadata["cache"]["hit"] is True
    assert events[-1].type == CoreEventType.COMPLETE.value

    token_events = [e for e in events if e.type == CoreEventType.TOKEN.value]
    assert "".join(e.content for e in token_events) == "hello world"

    generation_service.stream_generate.assert_not_called()
    caching_service.store.assert_not_awaited()


async def test_cache_miss_streams_live_and_stores_the_assembled_result() -> None:
    provider = _make_registered_provider()

    chunks = [
        StreamChunk(event=StreamEventType.START),
        StreamChunk(event=StreamEventType.TOKEN, content="hel"),
        StreamChunk(event=StreamEventType.TOKEN, content="lo"),
        StreamChunk(event=StreamEventType.COMPLETED),
    ]

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(return_value=CacheResult(hit=False))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert [e.type for e in events] == [
        StreamEventType.START.value,
        StreamEventType.TOKEN.value,
        StreamEventType.TOKEN.value,
        StreamEventType.COMPLETED.value,
    ]

    caching_service.store.assert_awaited_once()
    stored_result = caching_service.store.await_args.kwargs["result"]
    assert stored_result.content == "hello"
    assert stored_result.statistics.streamed is True


async def test_generation_error_mid_stream_yields_error_event_and_skips_store() -> None:
    provider = _make_registered_provider()

    async def _raising_stream():
        yield StreamChunk(event=StreamEventType.START)
        raise GenerationExecutionError("provider exploded")

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_raising_stream())

    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(return_value=CacheResult(hit=False))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert events[-1].type == CoreEventType.ERROR.value
    assert "provider exploded" in (events[-1].content or "")
    caching_service.store.assert_not_awaited()


async def test_streams_live_without_error_when_no_caching_service_is_wired() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert len(events) == 1
    assert events[0].content == "hi"


async def test_stream_artifact_is_persisted_on_successful_completion() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    artifact_writer = AsyncMock()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        artifact_writer=artifact_writer,
    )

    await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    artifact_writer.write.assert_awaited_once()
    written = artifact_writer.write.await_args.args[0]
    assert written.events[0].content == "hi"


async def test_stream_artifact_is_not_persisted_when_no_writer_wired() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        artifact_writer=None,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert len(events) == 1


async def test_stream_artifact_write_failure_does_not_break_the_stream() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = MagicMock()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    artifact_writer = AsyncMock()
    artifact_writer.write = AsyncMock(side_effect=RuntimeError("storage unavailable"))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        artifact_writer=artifact_writer,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert len(events) == 1
    assert events[0].content == "hi"
