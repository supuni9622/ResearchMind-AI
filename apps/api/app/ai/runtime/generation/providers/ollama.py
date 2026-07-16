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
    build_chat_messages,
)
from app.ai.runtime.generation.providers.helpers.structured import (
    build_ollama_format,
)
from app.ai.runtime.generation.providers.helpers.usage import (
    Usage,
)
from app.core.settings import (
    settings,
)
from ollama import (
    AsyncClient,
    RequestError,
    ResponseError,
)

logger = structlog.get_logger()


class OllamaProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(
            config,
        )

        self._client = AsyncClient(
            host=settings.ollama_host,
        )

    @property
    def provider(
        self,
    ) -> GenerationProvider:
        return GenerationProvider.OLLAMA

    ###########################################################################
    # Generation
    ###########################################################################

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = self.start_timer()

        logger.info(
            "generation.ollama.started",
            model=self.config.model_name,
        )

        response = await self._execute_with_retry(
            lambda: self._create_chat(
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

        content = response.message.content if response.message else ""

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
            "generation.ollama.completed",
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
        Native `format: <json_schema>` (wired in `_create_chat` /
        `stream` via `build_ollama_format`) whenever `output_schema`
        is set, falling back to `format: "json"` mode otherwise.
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
            "generation.ollama.stream.started",
            model=self.config.model_name,
        )

        try:
            stream = await self._client.chat(
                model=self.config.model_name,
                messages=build_chat_messages(
                    request,
                ),
                stream=True,
                options=self._build_options(
                    request,
                ),
                format=build_ollama_format(
                    request,
                ),
            )

            yield StreamChunk(
                event=StreamEventType.START,
            )

            async for chunk in stream:
                if chunk.message and chunk.message.content:
                    yield StreamChunk(
                        event=StreamEventType.TOKEN,
                        content=(chunk.message.content),
                    )

        except (
            RequestError,
            ResponseError,
            ConnectionError,
        ) as exc:
            logger.exception(
                "generation.ollama.stream.failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise GenerationExecutionError(
                str(exc),
            ) from exc

        logger.info(
            "generation.ollama.stream.completed",
            model=self.config.model_name,
        )

        yield StreamChunk(
            event=StreamEventType.COMPLETED,
        )

    ###########################################################################
    # Internals
    ###########################################################################

    async def _create_chat(
        self,
        request: GenerationRequest,
    ):

        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": build_chat_messages(
                request,
            ),
            "options": self._build_options(
                request,
            ),
        }

        format_type = build_ollama_format(
            request,
        )

        if format_type:
            kwargs["format"] = format_type

        #
        # Tool calling
        #

        if request.tools:
            kwargs["tools"] = [tool.model_dump() for tool in request.tools]

        return await self._client.chat(
            **kwargs,
        )

    ###########################################################################
    # Options Builder
    ###########################################################################

    def _build_options(
        self,
        request: GenerationRequest,
    ) -> dict[str, Any]:

        return {
            "temperature": (request.temperature or self.config.temperature),
            "num_predict": (request.max_tokens or self.config.max_tokens),
        }

    ###########################################################################
    # Usage Extraction
    ###########################################################################

    def _extract_usage(
        self,
        response,
    ) -> Usage:

        prompt_tokens = response.prompt_eval_count or 0

        completion_tokens = response.eval_count or 0

        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=(prompt_tokens + completion_tokens),
        )

    ###########################################################################
    # Health Check
    ###########################################################################

    async def health_check(
        self,
    ) -> bool:

        try:
            await self._client.ps()

            return True

        except Exception as exc:
            logger.warning(
                "generation.ollama.health_check_failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            return False

    ###########################################################################
    # Metadata
    ###########################################################################

    async def get_model_metadata(
        self,
    ) -> dict[str, Any]:

        metadata = await super().get_model_metadata()

        try:
            models = await self._client.list()

            metadata["installed_models"] = [model.model for model in models.models]

        except Exception as exc:
            logger.warning(
                "generation.ollama.list_models_failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            metadata["installed_models"] = []

        return metadata
