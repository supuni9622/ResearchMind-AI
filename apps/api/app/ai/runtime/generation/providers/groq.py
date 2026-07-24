from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

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
    build_groq_response_format,
)
from app.ai.runtime.generation.providers.helpers.usage import (
    Usage,
)
from app.core.settings import (
    settings,
)
from groq import (
    AsyncGroq,
    GroqError,
)
from groq.types.chat import (
    ChatCompletionMessageParam,
)

logger = structlog.get_logger()

_STRUCTURED_OUTPUT_TOOL_NAME = "emit_structured_response"


class GroqProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(
            config,
        )

        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
            timeout=config.timeout_seconds,
        )

    @property
    def provider(
        self,
    ) -> GenerationProvider:
        return GenerationProvider.GROQ

    ###########################################################################
    # Generation
    ###########################################################################

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = self.start_timer()

        logger.info(
            "generation.groq.started",
            model=self.config.model_name,
        )

        response = await self._execute_with_retry(
            lambda: self._create_completion(
                request,
            )
        )

        latency_ms = self.stop_timer(
            started,
        )

        usage = self._extract_usage(
            response,
        )

        message = response.choices[0].message

        tool_calls = message.tool_calls or []

        forced_call = next(
            (call for call in tool_calls if call.function.name == _STRUCTURED_OUTPUT_TOOL_NAME),
            None,
        )

        content = forced_call.function.arguments if forced_call else (message.content or "")

        parsed_output = None

        if request.response_format in (
            ResponseFormat.JSON,
            ResponseFormat.STRUCTURED,
        ):
            parsed_output = self.parse_structured_output(
                content,
            )

        statistics = self.build_statistics(
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        result = self.build_result(
            request=request,
            content=content,
            statistics=statistics,
            finish_reason=(response.choices[0].finish_reason),
            parsed_output=parsed_output,
            raw_response=response.model_dump(),
        )

        logger.info(
            "generation.groq.completed",
            model=self.config.model_name,
            latency_ms=latency_ms,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=statistics.total_tokens,
        )

        return result

    ###########################################################################
    # Streaming
    ###########################################################################

    async def stream(
        self,
        request: GenerationRequest,
    ) -> AsyncIterator[StreamChunk]:

        logger.info(
            "generation.groq.stream.started",
            model=self.config.model_name,
        )

        try:
            stream = await self._client.chat.completions.create(
                model=self.config.model_name,
                messages=cast(
                    list[ChatCompletionMessageParam],
                    build_chat_messages(
                        request,
                    ),
                ),
                stream=True,
                temperature=(request.temperature or self.config.temperature),
                max_completion_tokens=(request.max_tokens or self.config.max_tokens),
            )

            yield StreamChunk(
                event=StreamEventType.START,
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta.content

                if delta:
                    yield StreamChunk(
                        event=StreamEventType.TOKEN,
                        content=delta,
                    )

        except GroqError as exc:
            logger.exception(
                "generation.groq.stream.failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise GenerationExecutionError(
                str(exc),
            ) from exc

        logger.info(
            "generation.groq.stream.completed",
            model=self.config.model_name,
        )

        yield StreamChunk(
            event=StreamEventType.COMPLETED,
        )

    ###########################################################################
    # Internals
    ###########################################################################

    async def _create_completion(
        self,
        request: GenerationRequest,
    ):

        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "messages": build_chat_messages(
                request,
            ),
            "temperature": (request.temperature or self.config.temperature),
            "max_completion_tokens": (request.max_tokens or self.config.max_tokens),
        }

        #
        # Structured Outputs -- forced tool call
        #
        # Groq only enables native `response_format: json_schema` for a
        # narrow, provider-curated model allowlist that excludes
        # `llama-3.3-70b-versatile` (this platform's default/AUTO-routed
        # Groq model -- see `build_groq_response_format`), so structured
        # requests fall back to plain `json_object` mode with the schema
        # spelled out as prose in the prompt. That's schema-*unenforced*:
        # the model occasionally drifts (missing/extra fields, wrong enum
        # casing, wrong task count) even after a regeneration attempt --
        # confirmed in production via repeated `ResearchPlannerError`s on
        # the research planner. Tool/function calling, unlike the narrow
        # Structured Outputs allowlist, is broadly supported on Groq
        # (including this model) and is what the model was fine-tuned to
        # follow precisely, so forcing a single tool call whose
        # `parameters` *is* the output schema constrains the response
        # shape far more reliably than prompt-only JSON mode. The
        # resulting `tool_calls[0].function.arguments` is read back as
        # `content` in `generate()`.
        #

        if request.response_format == ResponseFormat.STRUCTURED and request.output_schema:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": _STRUCTURED_OUTPUT_TOOL_NAME,
                        "description": "Return the response matching the required schema.",
                        "parameters": request.output_schema,
                    },
                }
            ]
            kwargs["tool_choice"] = {
                "type": "function",
                "function": {"name": _STRUCTURED_OUTPUT_TOOL_NAME},
            }

            return await self._client.chat.completions.create(
                **kwargs,
            )

        #
        # JSON Mode
        #

        response_format = build_groq_response_format(
            request,
        )

        if response_format:
            kwargs["response_format"] = response_format

        #
        # Future tool calling
        #

        if request.tools:
            kwargs["tools"] = [tool.model_dump() for tool in request.tools]

        return await self._client.chat.completions.create(
            **kwargs,
        )

    ###########################################################################
    # Usage
    ###########################################################################

    def _extract_usage(
        self,
        response,
    ) -> Usage:

        usage = response.usage

        if usage is None:
            return Usage()

        return Usage(
            prompt_tokens=(usage.prompt_tokens),
            completion_tokens=(usage.completion_tokens),
            total_tokens=(usage.total_tokens),
        )

    ###########################################################################
    # Structured Outputs
    ###########################################################################

    async def generate_structured(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Native `response_format: json_schema` (wired in
        `_create_completion` via `build_groq_response_format`)
        whenever `output_schema` is set, falling back to plain
        JSON mode otherwise.
        """

        return await self.generate(
            request,
        )
