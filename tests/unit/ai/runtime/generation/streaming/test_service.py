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
- Live streaming traces through the wired RuntimeTracer and records/persists
  observability metrics on successful completion, but skips both when the
  stream fails mid-way (mirrors GenerationService.generate()'s own shape)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.ai.artifacts.enums import ArtifactCategory, ArtifactPolicy, ArtifactRuntime
from app.ai.artifacts.policies.models import ArtifactPolicyRule
from app.ai.artifacts.policies.service import ArtifactPolicyService
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
from app.ai.runtime.generation.routing.enums import RoutingStrategy
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


def _make_generation_service() -> MagicMock:
    """
    GenerationService double whose score_completed_stream() is an
    identity passthrough (returns whatever result it was given
    unchanged) -- individual tests still set resolve_streaming_provider/
    stream_generate themselves.
    """
    service = MagicMock()
    service.score_completed_stream = AsyncMock(side_effect=lambda *, request, result: result)
    return service


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
    generation_artifact_writer: AsyncMock | None = None,
    artifact_policy_service: ArtifactPolicyService | None = None,
    metrics_service: MagicMock | None = None,
    observability_service: AsyncMock | None = None,
    tracer: MagicMock | None = None,
    usage_service: AsyncMock | None = None,
) -> StreamingService:
    return StreamingService(
        generation_service=generation_service,
        registry=GenerationRegistry(providers=[provider]),
        event_adapter=get_event_adapter(),
        caching_service=caching_service,
        artifact_writer=artifact_writer,
        generation_artifact_writer=generation_artifact_writer,
        artifact_policy_service=artifact_policy_service,
        metrics_service=metrics_service,
        observability_service=observability_service,
        tracer=tracer,
        usage_service=usage_service,
    )


async def test_cache_hit_is_replayed_as_synthetic_events_without_live_streaming() -> None:
    provider = _make_registered_provider()

    generation_service = _make_generation_service()
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


async def test_cache_hit_records_zero_cost_owner_scoped_usage() -> None:
    provider = _make_registered_provider()
    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(
        return_value=CacheResult(
            hit=True,
            level=CacheLevel.EXACT,
            generation_result=_make_result("cached answer"),
        )
    )
    usage_service = AsyncMock()
    request = _make_request()
    request.owner_id = uuid4()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
        usage_service=usage_service,
    )

    await _collect(service.stream_generate(request=request, provider=GenerationProvider.GROQ))

    recorded = usage_service.record.await_args.args[0]
    assert recorded.request is request
    assert recorded.statistics.cache_hit is True
    assert recorded.statistics.streamed is True
    assert recorded.statistics.estimated_cost_usd == 0


async def test_cache_hit_replay_events_carry_the_original_results_generation_id() -> None:
    """
    E21 (EVALUATION_IMPLEMENTATION_TRACKER.md): the frontend needs a
    generation_id on stream events to submit POST /feedback against the
    right row. For a cache hit, that must be the *original* cached
    result's generation_id -- the same one usage_service.record() reuses
    via model_copy() just above -- not a freshly-minted one that
    wouldn't match anything in GenerationUsage.
    """

    provider = _make_registered_provider()
    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    cached_result = _make_result("hello world")
    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(
        return_value=CacheResult(hit=True, level=CacheLevel.EXACT, generation_result=cached_result)
    )

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert events[0].metadata["generation_id"] == str(cached_result.generation_id)


async def test_cache_miss_streams_live_and_stores_the_assembled_result() -> None:
    provider = _make_registered_provider()

    chunks = [
        StreamChunk(event=StreamEventType.START),
        StreamChunk(event=StreamEventType.TOKEN, content="hel"),
        StreamChunk(event=StreamEventType.TOKEN, content="lo"),
        StreamChunk(event=StreamEventType.COMPLETED),
    ]

    generation_service = _make_generation_service()
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


async def test_completed_stream_records_owner_scoped_usage() -> None:
    provider = _make_registered_provider()
    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(
        return_value=_fake_stream([StreamChunk(event=StreamEventType.TOKEN, content="hello")])
    )
    usage_service = AsyncMock()
    request = _make_request()
    request.owner_id = uuid4()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        usage_service=usage_service,
    )

    await _collect(service.stream_generate(request=request, provider=GenerationProvider.GROQ))

    recorded = usage_service.record.await_args.args[0]
    assert recorded.request is request
    assert recorded.statistics.streamed is True
    assert recorded.statistics.routing_strategy is None


async def test_live_stream_events_carry_a_generation_id_matching_the_persisted_row() -> None:
    """
    E21: every event on the live (non-cache) path must carry the same
    generation_id that ends up in the persisted GenerationUsage row, so
    the frontend can submit POST /feedback against a row that actually
    exists.
    """

    provider = _make_registered_provider()
    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(
        return_value=_fake_stream(
            [
                StreamChunk(event=StreamEventType.TOKEN, content="hel"),
                StreamChunk(event=StreamEventType.TOKEN, content="lo"),
                StreamChunk(event=StreamEventType.COMPLETED),
            ]
        )
    )
    usage_service = AsyncMock()
    request = _make_request()
    request.owner_id = uuid4()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        usage_service=usage_service,
    )

    events = await _collect(
        service.stream_generate(request=request, provider=GenerationProvider.GROQ)
    )

    recorded = usage_service.record.await_args.args[0]
    generation_ids = {e.metadata.get("generation_id") for e in events}
    assert generation_ids == {str(recorded.generation_id)}


async def test_stream_generate_with_no_provider_records_the_resolved_routing_strategy() -> None:
    """
    Regression test for a real bug (EVALUATION_IMPLEMENTATION_TRACKER.md
    E8's "Update" note, 2026-08-11): when `stream_generate()` is called
    with no explicit `provider` (the real production shape -- Chat/
    Linear/Deep Research never pass one), routing resolves a provider via
    `resolve_streaming_provider()`, but the *strategy* that resolved it
    was previously dropped entirely -- `GenerationRequest.routing_strategy`
    stays `None` (no caller sets an explicit override), and nothing ever
    wrote the effective strategy anywhere else, so every real
    `GenerationUsage` row persisted `routing_strategy=NULL` despite a
    routing decision genuinely having been made every time. Fixed by
    threading the resolved strategy through to
    `GenerationResult.statistics.routing_strategy`, mirroring
    `GenerationService._generate_with_routing()`'s non-streaming fix.
    """

    provider = _make_registered_provider()
    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(
        return_value=_fake_stream([StreamChunk(event=StreamEventType.TOKEN, content="hello")])
    )
    usage_service = AsyncMock()
    request = _make_request()
    request.owner_id = uuid4()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        usage_service=usage_service,
    )

    await _collect(service.stream_generate(request=request))

    generation_service.resolve_streaming_provider.assert_called_once_with(request)
    recorded = usage_service.record.await_args.args[0]
    assert recorded.statistics.routing_strategy == RoutingStrategy.AUTO


async def test_completed_stream_is_scored_via_the_generation_service() -> None:
    """
    `_stream_live()` has no guardrail/validation service of its own --
    scoring an already-completed stream is delegated to
    `GenerationService.score_completed_stream()` (informational only,
    never blocking), which the caching/artifact/metrics steps then see
    the (possibly updated) result from.
    """
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    scored_result = _make_result("hi")
    generation_service.score_completed_stream = AsyncMock(return_value=scored_result)

    caching_service = AsyncMock()
    caching_service.lookup = AsyncMock(return_value=CacheResult(hit=False))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=caching_service,
    )

    await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    generation_service.score_completed_stream.assert_awaited_once()
    call_kwargs = generation_service.score_completed_stream.await_args.kwargs
    assert call_kwargs["result"].content == "hi"

    # The (possibly-updated) scored result, not the pre-scoring one, is
    # what gets cached.
    caching_service.store.assert_awaited_once()
    assert caching_service.store.await_args.kwargs["result"] is scored_result


async def test_generation_error_mid_stream_yields_error_event_and_skips_store() -> None:
    provider = _make_registered_provider()

    async def _raising_stream():
        yield StreamChunk(event=StreamEventType.START)
        raise GenerationExecutionError("provider exploded")

    generation_service = _make_generation_service()
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

    generation_service = _make_generation_service()
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


async def test_live_stream_is_traced_and_metrics_recorded_on_success() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    tracer = MagicMock()
    trace_run_id = uuid4()
    tracer.trace.return_value.__enter__.return_value.run_id = trace_run_id
    metrics_service = MagicMock()
    observability_service = AsyncMock()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        metrics_service=metrics_service,
        observability_service=observability_service,
        tracer=tracer,
    )

    await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    tracer.trace.assert_called_once()
    assert tracer.trace.call_args.kwargs["name"] == "generation"
    assert tracer.trace.call_args.kwargs["inputs"] == {"prompt": _make_request().user_prompt}
    assert tracer.trace.call_args.kwargs["tags"]["provider"] == GenerationProvider.GROQ.value
    assert tracer.trace.call_args.kwargs["tags"]["streamed"] is True
    assert tracer.trace.call_args.kwargs["tags"]["owner_id"] is None

    trace_handle = tracer.trace.return_value.__enter__.return_value
    trace_handle.set_output.assert_called_once_with(content="hi")

    metrics_service.record.assert_called_once()
    recorded_result = metrics_service.record.call_args.args[0]
    assert recorded_result.content == "hi"
    assert recorded_result.langsmith_run_id == trace_run_id
    assert recorded_result.statistics.streamed is True

    observability_service.record_generation.assert_awaited_once()
    assert observability_service.record_generation.await_args.kwargs["metrics"] is (
        metrics_service.record.return_value
    )


async def test_no_metrics_recorded_when_generation_error_mid_stream() -> None:
    provider = _make_registered_provider()

    async def _raising_stream():
        yield StreamChunk(event=StreamEventType.START)
        raise GenerationExecutionError("provider exploded")

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_raising_stream())

    metrics_service = MagicMock()
    observability_service = AsyncMock()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        metrics_service=metrics_service,
        observability_service=observability_service,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert events[-1].type == CoreEventType.ERROR.value
    metrics_service.record.assert_not_called()
    observability_service.record_generation.assert_not_awaited()


async def test_stream_artifact_is_persisted_on_successful_completion() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
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

    generation_service = _make_generation_service()
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

    generation_service = _make_generation_service()
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


# ==============================================================
# GenerationArtifact persistence (Evaluation Platform Gap 1,
# streaming-specific follow-up, 2026-08-12) -- previously only
# StreamArtifact (category STREAM, no request/response content) was
# persisted for a genuinely streamed call, regardless of the
# (runtime, GENERATION) policy, because this path never called the
# shared persist_generation_artifact() logic GenerationService.generate()
# uses. That silently meant the online-scoring job (which reads
# GenerationArtifact specifically) could never score real streamed
# traffic for any surface.
# ==============================================================


async def test_generation_artifact_is_persisted_on_successful_stream_completion() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    generation_artifact_writer = AsyncMock()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        generation_artifact_writer=generation_artifact_writer,
        # Default request has no artifact_runtime -> falls back to CHAT,
        # whose (CHAT, GENERATION) policy is SESSION (real default rules,
        # not a fake) -- proves this isn't gated behind a test-only policy.
        artifact_policy_service=ArtifactPolicyService(),
    )

    await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    generation_artifact_writer.write.assert_awaited_once()
    written = generation_artifact_writer.write.await_args.args[0]
    assert written.response.content == "hi"


async def test_generation_artifact_is_not_persisted_when_no_writer_wired() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        generation_artifact_writer=None,
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert len(events) == 1


async def test_generation_artifact_respects_the_artifact_policy() -> None:
    """A runtime/category combination with no policy rule must not
    persist, mirroring GenerationService.generate()'s own behavior --
    proves this new call site actually goes through the same policy
    check, not an unconditional write."""

    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    generation_artifact_writer = AsyncMock()

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        generation_artifact_writer=generation_artifact_writer,
        artifact_policy_service=ArtifactPolicyService(
            rules=[
                ArtifactPolicyRule(
                    runtime=ArtifactRuntime.CHAT,
                    category=ArtifactCategory.GENERATION,
                    policy=ArtifactPolicy.NEVER,
                ),
            ]
        ),
    )

    await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    generation_artifact_writer.write.assert_not_awaited()


async def test_generation_artifact_write_failure_does_not_break_the_stream() -> None:
    provider = _make_registered_provider()

    chunks = [StreamChunk(event=StreamEventType.TOKEN, content="hi")]

    generation_service = _make_generation_service()
    generation_service.resolve_streaming_provider = MagicMock(return_value=GenerationProvider.GROQ)
    generation_service.stream_generate = MagicMock(return_value=_fake_stream(chunks))

    generation_artifact_writer = AsyncMock()
    generation_artifact_writer.write = AsyncMock(side_effect=RuntimeError("storage unavailable"))

    service = _make_service(
        generation_service=generation_service,
        provider=provider,
        caching_service=None,
        generation_artifact_writer=generation_artifact_writer,
        artifact_policy_service=ArtifactPolicyService(),
    )

    events = await _collect(
        service.stream_generate(request=_make_request(), provider=GenerationProvider.GROQ)
    )

    assert len(events) == 1
    assert events[0].content == "hi"
