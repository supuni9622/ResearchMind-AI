from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

import structlog
from anthropic import AnthropicError, AsyncAnthropic
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
)
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.providers.base import (
    BaseGenerationProvider,
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
        super().__init__(config)

        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
        )

    @property
    def provider(
        self,
    ):
        return GenerationProvider.CLAUDE

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = perf_counter()

        logger.info(
            "generation.claude.started",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        try:
            response = await self._client.messages.create(
                model=self.config.model_name,
                max_tokens=self.config.max_tokens,
                system=request.system_prompt or "",
                messages=[
                    {
                        "role": "user",
                        "content": (request.prompt_context.context + "\n\n" + request.user_prompt),
                    }
                ],
            )
        except AnthropicError as exc:
            logger.error(
                "generation.claude.failed",
                provider=self.provider.value,
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(f"Claude generation failed: {exc}") from exc

        duration = (perf_counter() - started) * 1000

        content = "\n".join(block.text for block in response.content if block.type == "text")

        result = GenerationResult(
            request=request,
            execution=GenerationExecution(completed_at=datetime.now(UTC)),
            statistics=GenerationStatistics(
                provider=self.provider,
                model=self.config.model_name,
                latency_ms=duration,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=(response.usage.input_tokens + response.usage.output_tokens),
            ),
            provider=self.provider,
            model=self.config.model_name,
            content=content,
        )

        logger.info(
            "generation.claude.completed",
            provider=self.provider.value,
            model=self.config.model_name,
            latency_ms=duration,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
        )

        return result
