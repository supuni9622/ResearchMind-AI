from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
    ResponseFormat,
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
    build_gemini_generation_config,
)
from app.ai.runtime.generation.providers.helpers.usage import (
    Usage,
)
from app.core.settings import (
    settings,
)
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = structlog.get_logger()


class GeminiProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(
            config,
        )

        self._client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    @property
    def provider(
        self,
    ) -> GenerationProvider:
        return GenerationProvider.GEMINI

    ###########################################################################
    # Generation
    ###########################################################################

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = self.start_timer()

        logger.info(
            "generation.gemini.started",
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

        content = response.text or ""

        parsed_output = None

        if request.response_format in (
            ResponseFormat.JSON,
            ResponseFormat.STRUCTURED,
        ):
            parsed_output = self.parse_structured_output(
                content,
            )

        result = self.build_result(
            request=request,
            content=content,
            statistics=statistics,
            parsed_output=parsed_output,
            raw_response=response.model_dump(),
        )

        logger.info(
            "generation.gemini.completed",
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
        Native `response_mime_type` + `response_json_schema` (wired in
        `_build_generation_config` via `build_gemini_generation_config`)
        whenever `output_schema` is set.
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
            "generation.gemini.stream.started",
            model=self.config.model_name,
        )

        config = self._build_generation_config(
            request,
        )

        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=self.config.model_name,
                contents=build_prompt_text(
                    request,
                ),
                config=config,
            )

            yield StreamChunk(
                event=StreamEventType.START,
            )

            async for chunk in stream:
                if chunk.text:
                    yield StreamChunk(
                        event=StreamEventType.TOKEN,
                        content=chunk.text,
                    )

        except APIError as exc:
            logger.exception(
                "generation.gemini.stream.failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise GenerationExecutionError(
                str(exc),
            ) from exc

        logger.info(
            "generation.gemini.stream.completed",
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

        config = self._build_generation_config(
            request,
        )

        return await self._client.aio.models.generate_content(
            model=self.config.model_name,
            contents=build_prompt_text(
                request,
            ),
            config=config,
        )

    ###########################################################################
    # Generation Config Builder
    ###########################################################################

    def _build_generation_config(
        self,
        request: GenerationRequest,
    ) -> types.GenerateContentConfig:

        kwargs: dict[str, Any] = {}

        if request.system_prompt:
            kwargs["system_instruction"] = request.system_prompt

        kwargs["temperature"] = request.temperature or self.config.temperature

        kwargs["max_output_tokens"] = request.max_tokens or self.config.max_tokens

        #
        # JSON Mode
        #

        structured_config = build_gemini_generation_config(
            request,
        )

        kwargs.update(
            structured_config,
        )

        #
        # Future Tool Calling
        #

        if request.tools:
            kwargs["tools"] = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=tool.name,
                            description=tool.description,
                            parameters_json_schema=tool.parameters,
                        )
                    ]
                )
                for tool in request.tools
            ]

        return types.GenerateContentConfig(
            **kwargs,
        )

    ###########################################################################
    # Usage
    ###########################################################################

    def _extract_usage(
        self,
        response,
    ) -> Usage:

        usage = response.usage_metadata

        if usage is None:
            return Usage()

        reasoning_tokens = getattr(
            usage,
            "thoughts_token_count",
            0,
        )

        return Usage(
            prompt_tokens=(usage.prompt_token_count or 0),
            completion_tokens=(usage.candidates_token_count or 0),
            reasoning_tokens=(reasoning_tokens or 0),
            total_tokens=(usage.total_token_count or 0),
        )

    ###########################################################################
    # Health Check
    ###########################################################################

    async def health_check(
        self,
    ) -> bool:

        try:
            await self._client.aio.models.generate_content(
                model=self.config.model_name,
                contents="ping",
            )

            return True

        except Exception as exc:
            logger.warning(
                "generation.gemini.health_check_failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            return False
