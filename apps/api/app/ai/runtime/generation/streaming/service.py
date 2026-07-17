from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

import structlog
from app.ai.runtime.events.enums import (
    CoreEventType,
    EventCategory,
)
from app.ai.runtime.events.interfaces import (
    ProviderEventAdapterInterface,
)
from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.caching.service import (
    CachingService,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.exceptions import (
    GenerationError,
)
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.models import (
    StreamEventType as ProviderStreamEventType,
)
from app.ai.runtime.generation.registry import (
    GenerationRegistry,
)
from app.ai.runtime.generation.service import (
    GenerationService,
)
from app.ai.runtime.generation.streaming.models import (
    StreamCacheOutcome,
)

logger = structlog.get_logger()

#
# Cache replay chunks the cached content back into synthetic TOKEN events
# so a hit still satisfies the streaming contract a caller asked for (see
# ADR-028 "Cache Integration"). Chunked by character count rather than by
# word so that concatenating every TOKEN event's `content` in order (via
# `"".join(...)`, exactly how a consumer reconstructs a live stream's
# content) always reproduces the cached string exactly -- this is not
# meant to reproduce the original provider's actual chunk boundaries,
# which can't be recovered from a single cached string.
#
_REPLAY_CHUNK_CHARS = 12


class StreamingService:
    """
    Generation Streaming Platform orchestrator.

    Sits between the API layer and `GenerationService.stream_generate()`:
    resolves which provider/model a request will use, checks the Runtime
    Cache first (replaying a hit as synthetic TOKEN events rather than
    skipping the stream contract), and otherwise streams live -- converting
    each provider StreamChunk into a canonical StreamEvent via the Runtime
    Event Platform's adapter, then storing the assembled result once the
    stream completes.
    """

    def __init__(
        self,
        *,
        generation_service: GenerationService,
        registry: GenerationRegistry,
        event_adapter: ProviderEventAdapterInterface,
        caching_service: CachingService | None = None,
    ) -> None:
        self._generation_service = generation_service
        self._registry = registry
        self._event_adapter = event_adapter
        self._caching_service = caching_service

    async def stream_generate(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider | None = None,
    ) -> AsyncGenerator[StreamEvent, None]:

        resolved_provider = provider or self._generation_service.resolve_streaming_provider(
            request,
        )

        generation_provider = self._registry.get(
            resolved_provider,
        )

        if self._caching_service is not None:
            cache_result = await self._caching_service.lookup(
                request=request,
                provider=resolved_provider,
                model=generation_provider.config.model_name,
                routing_strategy=request.routing_strategy,
            )

            if cache_result.hit:
                async for event in self._replay_cache_hit(
                    request=request,
                    cache_result_level=cache_result.level,
                    content=cache_result.generation_result.content
                    if cache_result.generation_result
                    else "",
                ):
                    yield event
                return

        async for event in self._stream_live(
            request=request,
            provider=resolved_provider,
            generation_provider_config_model=generation_provider.config.model_name,
        ):
            yield event

    # ==========================================================
    # Cache hit replay
    # ==========================================================

    async def _replay_cache_hit(
        self,
        *,
        request: GenerationRequest,
        cache_result_level: Any,
        content: str,
    ) -> AsyncGenerator[StreamEvent, None]:

        logger.info(
            "streaming.cache.replay",
            level=(cache_result_level.value if cache_result_level else None),
        )

        yield self._event(
            request=request,
            event_type=CoreEventType.START,
            metadata={
                "cache": StreamCacheOutcome(
                    hit=True,
                    level=cache_result_level,
                    replayed=True,
                ).model_dump(mode="json"),
            },
        )

        for index in range(0, len(content), _REPLAY_CHUNK_CHARS):
            yield self._event(
                request=request,
                event_type=CoreEventType.TOKEN,
                content=content[index : index + _REPLAY_CHUNK_CHARS],
            )

        yield self._event(
            request=request,
            event_type=CoreEventType.COMPLETE,
        )

    # ==========================================================
    # Live streaming
    # ==========================================================

    async def _stream_live(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider,
        generation_provider_config_model: str,
    ) -> AsyncGenerator[StreamEvent, None]:

        content_parts: list[str] = []

        started = perf_counter()

        try:
            async for chunk in self._generation_service.stream_generate(
                request=request,
                provider=provider,
            ):
                if chunk.event == ProviderStreamEventType.TOKEN and chunk.content:
                    content_parts.append(chunk.content)

                yield self._event_adapter.to_stream_event(
                    chunk,
                    session_id=request.session_id,
                    request_id=request.request_id,
                )
        except GenerationError as exc:
            logger.warning(
                "streaming.live.failed",
                provider=provider.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            yield self._event(
                request=request,
                event_type=CoreEventType.ERROR,
                content=str(exc),
            )
            return
        except Exception as exc:
            logger.exception(
                "streaming.live.unexpected_error",
                provider=provider.value,
                error_type=type(exc).__name__,
            )
            yield self._event(
                request=request,
                event_type=CoreEventType.ERROR,
                content="Unexpected streaming failure.",
            )
            return

        if self._caching_service is None:
            return

        await self._store_completed_stream(
            request=request,
            provider=provider,
            model=generation_provider_config_model,
            content="".join(content_parts),
            latency_ms=(perf_counter() - started) * 1000,
        )

    async def _store_completed_stream(
        self,
        *,
        request: GenerationRequest,
        provider: GenerationProvider,
        model: str,
        content: str,
        latency_ms: float,
    ) -> None:
        """
        Best-effort statistics: today's provider `stream()` implementations
        only yield content deltas, not token/cost usage (see
        `generation/providers/*.py`), so prompt/completion tokens here are
        `count_tokens()` estimates rather than provider-reported figures.
        Known, accepted gap -- not blocking cache-store on upgrading every
        provider's streaming SDK call to request usage.
        """

        generation_provider = self._registry.get(provider)

        prompt_tokens = await generation_provider.count_tokens(
            request.user_prompt,
        )
        completion_tokens = await generation_provider.count_tokens(
            content,
        )

        assert self._caching_service is not None

        await self._caching_service.store(
            request=request,
            provider=provider,
            model=model,
            routing_strategy=request.routing_strategy,
            result=GenerationResult(
                request=request,
                execution=GenerationExecution(
                    completed_at=datetime.now(UTC),
                ),
                statistics=GenerationStatistics(
                    provider=provider,
                    model=model,
                    latency_ms=latency_ms,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                    streamed=True,
                    estimated_cost_usd=generation_provider.estimate_cost(
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    ),
                ),
                provider=provider,
                model=model,
                content=content,
            ),
        )

    # ==========================================================
    # Event helper
    # ==========================================================

    def _event(
        self,
        *,
        request: GenerationRequest,
        event_type: CoreEventType,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StreamEvent:

        return StreamEvent(
            session_id=request.session_id,
            request_id=request.request_id,
            category=EventCategory.GENERATION,
            type=event_type.value,
            content=content,
            metadata=metadata or {},
        )
