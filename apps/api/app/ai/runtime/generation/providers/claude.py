from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, cast

import structlog
from anthropic import (
    AnthropicError,
    AsyncAnthropic,
)
from anthropic.types import (
    MessageParam,
)
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
    build_claude_messages,
)
from app.ai.runtime.generation.providers.helpers.structured import (
    build_claude_json_instruction,
    build_claude_output_config,
)
from app.ai.runtime.generation.providers.helpers.usage import (
    Usage,
)
from app.core.settings import settings

logger = structlog.get_logger()


class ClaudeProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(
            config,
        )

        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            timeout=config.timeout_seconds,
        )

    @property
    def provider(
        self,
    ) -> GenerationProvider:
        return GenerationProvider.CLAUDE

    ###########################################################################
    # Generation
    ###########################################################################

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = self.start_timer()

        logger.info(
            "generation.claude.started",
            model=self.config.model_name,
        )

        response = await self._execute_with_retry(
            lambda: self._create_message(
                request,
            )
        )

        latency_ms = self.stop_timer(
            started,
        )

        usage = self._extract_usage(
            response,
        )

        content = self._extract_content(
            response,
        )

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

        tool_calls = self._extract_tool_calls(
            response,
        )

        result = self.build_result(
            request=request,
            content=content,
            statistics=statistics,
            finish_reason=response.stop_reason,
            parsed_output=parsed_output,
            tool_calls=tool_calls,
            raw_response=response.model_dump(),
        )

        logger.info(
            "generation.claude.completed",
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
            "generation.claude.stream.started",
            model=self.config.model_name,
        )

        system_prompt, messages = build_claude_messages(
            request,
        )

        try:
            stream = await self._client.messages.create(
                model=self.config.model_name,
                system=(system_prompt or ""),
                messages=cast(
                    list[MessageParam],
                    messages,
                ),
                max_tokens=(request.max_tokens or self.config.max_tokens),
                temperature=(request.temperature or self.config.temperature),
                stream=True,
            )

            yield StreamChunk(
                event=StreamEventType.START,
            )

            async for event in stream:
                #
                # text deltas
                #

                if event.type == "content_block_delta":
                    delta = getattr(
                        event.delta,
                        "text",
                        None,
                    )

                    if delta:
                        yield StreamChunk(
                            event=StreamEventType.TOKEN,
                            content=delta,
                        )

        except AnthropicError as exc:
            logger.exception(
                "generation.claude.stream.failed",
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise GenerationExecutionError(
                str(exc),
            ) from exc

        logger.info(
            "generation.claude.stream.completed",
            model=self.config.model_name,
        )

        yield StreamChunk(
            event=StreamEventType.COMPLETED,
        )

    ###########################################################################
    # Structured Generation
    ###########################################################################

    async def generate_structured(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """
        Structured generation.

        Preferred:

        Native `output_config.format` (schema-constrained JSON,
        wired in `_create_message` whenever `output_schema` is set).

        Fallback:

        Prompt enforced JSON when no schema is available.
        """

        return await self.generate(
            request,
        )

    ###########################################################################
    # Internals
    ###########################################################################

    async def _create_message(
        self,
        request: GenerationRequest,
    ):

        system_prompt, messages = build_claude_messages(
            request,
        )

        kwargs: dict[str, Any] = {
            "model": self.config.model_name,
            "system": (system_prompt or ""),
            "messages": messages,
            "max_tokens": (request.max_tokens or self.config.max_tokens),
            "temperature": (request.temperature or self.config.temperature),
        }

        #
        # Structured Outputs
        #
        # Native `output_config.format` (schema-constrained decoding) is
        # preferred whenever a schema is available. Otherwise fall back
        # to a prompt-enforced JSON instruction.
        #

        output_config = build_claude_output_config(
            request,
        )

        if output_config:
            kwargs["output_config"] = output_config

        elif request.response_format in (
            ResponseFormat.JSON,
            ResponseFormat.STRUCTURED,
        ):
            kwargs["system"] = (
                (system_prompt or "")
                + "\n"
                + build_claude_json_instruction(
                    request,
                )
            )

        #
        # Tool Calling
        #

        if request.tools:
            kwargs["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": (tool.parameters),
                }
                for tool in request.tools
            ]

        return await self._client.messages.create(
            **kwargs,
        )

    ###########################################################################
    # Helpers
    ###########################################################################

    def _extract_content(
        self,
        response,
    ) -> str:

        texts: list[str] = []

        for block in response.content:
            if (
                getattr(
                    block,
                    "type",
                    None,
                )
                == "text"
            ):
                texts.append(
                    block.text,
                )

        return "\n".join(
            texts,
        )

    def _extract_tool_calls(
        self,
        response,
    ) -> list[Any]:

        tool_calls = []

        for block in response.content:
            if (
                getattr(
                    block,
                    "type",
                    None,
                )
                == "tool_use"
            ):
                tool_calls.append(
                    {
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        return tool_calls

    def _extract_usage(
        self,
        response,
    ) -> Usage:

        usage = response.usage

        if usage is None:
            return Usage()

        total = usage.input_tokens + usage.output_tokens

        return Usage(
            prompt_tokens=(usage.input_tokens),
            completion_tokens=(usage.output_tokens),
            total_tokens=total,
        )
