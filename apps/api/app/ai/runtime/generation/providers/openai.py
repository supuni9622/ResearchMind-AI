from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
    StreamChunk,
    StreamEventType,
)
from app.ai.runtime.generation.providers.base import (
    BaseGenerationProvider,
)
from app.ai.runtime.generation.providers.helpers.prompt_builder import (
    build_prompt_text,
)
from app.ai.runtime.generation.providers.helpers.structured import (
    build_openai_text_config,
)
from app.ai.runtime.generation.providers.helpers.usage import (
    Usage,
)
from app.core.settings import settings
from openai import (
    AsyncOpenAI,
    OpenAIError,
)

logger = structlog.get_logger()


class OpenAIProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(
            config,
        )

        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=config.timeout_seconds,
        )

    @property
    def provider(
        self,
    ) -> GenerationProvider:
        return GenerationProvider.OPENAI

    ###########################################################################
    # Generation
    ###########################################################################

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = self.start_timer()

        logger.info(
            "generation.openai.started",
            model=self.config.model_name,
        )

        response = await self._execute_with_retry(
            lambda: self._create_response(
                request,
            )
        )

        latency_ms = self.stop_timer(
            started,
        )

        usage = self._extract_usage(
            response,
        )

        statistics = self.build_statistics(
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            reasoning_tokens=usage.reasoning_tokens,
        )

        parsed_output = None

        if request.output_schema:
            parsed_output = self.parse_structured_output(
                response.output_text,
            )

        result = self.build_result(
            request=request,
            content=response.output_text or "",
            statistics=statistics,
            parsed_output=parsed_output,
            raw_response=response.model_dump(),
        )

        logger.info(
            "generation.openai.completed",
            model=self.config.model_name,
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=statistics.total_tokens,
        )

        return result

    ###########################################################################
    # Structured Outputs
    ###########################################################################

    async def generate_structured(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Native `text.format: json_schema` (wired in `_create_response`
        via `build_openai_text_config`) whenever `output_schema` is set,
        falling back to `json_object` mode otherwise.
        """

        return await self.generate(
            request,
        )

    ###########################################################################
    # Streaming
    ###########################################################################

    async def stream(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[StreamChunk]:

        logger.info(
            "generation.openai.stream.started",
            model=self.config.model_name,
        )

        try:
            stream = await self._client.responses.create(
                model=self.config.model_name,
                input=build_prompt_text(
                    request,
                ),
                stream=True,
            )

            yield StreamChunk(
                event=StreamEventType.START,
            )

            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield StreamChunk(
                        event=StreamEventType.TOKEN,
                        content=event.delta,
                    )

        except OpenAIError as exc:
            logger.exception(
                "generation.openai.stream.failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise GenerationExecutionError(
                str(exc),
            ) from exc

        logger.info(
            "generation.openai.stream.completed",
            model=self.config.model_name,
        )

        yield StreamChunk(
            event=StreamEventType.COMPLETED,
        )

    ###########################################################################
    # Internals
    ###########################################################################

    async def _create_response(
        self,
        request: GenerationRequest,
    ):

        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "input": build_prompt_text(
                request,
            ),
        }

        if request.temperature is not None:
            kwargs["temperature"] = request.temperature

        if request.max_tokens:
            kwargs["max_output_tokens"] = request.max_tokens

        text_config = build_openai_text_config(
            request,
        )

        if text_config:
            kwargs["text"] = text_config

        #
        # Future tool calling
        #

        if request.tools:
            kwargs["tools"] = [tool.model_dump() for tool in request.tools]

        return await self._client.responses.create(
            **kwargs,
        )

    ###########################################################################
    # Usage Extraction
    ###########################################################################

    def _extract_usage(
        self,
        response,
    ) -> Usage:

        usage = response.usage

        if usage is None:
            return Usage()

        reasoning_tokens = getattr(
            usage,
            "reasoning_tokens",
            0,
        )

        cached_tokens = getattr(
            usage,
            "cached_tokens",
            0,
        )

        return Usage(
            prompt_tokens=(usage.input_tokens),
            completion_tokens=(usage.output_tokens),
            reasoning_tokens=(reasoning_tokens),
            cached_tokens=(cached_tokens),
            total_tokens=(usage.total_tokens),
        )
