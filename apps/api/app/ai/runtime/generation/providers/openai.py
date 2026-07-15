from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter

import structlog
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
from openai import AsyncOpenAI, OpenAIError

logger = structlog.get_logger()


class OpenAIProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(config)

        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
        )

    @property
    def provider(
        self,
    ):
        return GenerationProvider.OPENAI

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = perf_counter()

        logger.info(
            "generation.openai.started",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        try:
            response = await self._client.responses.create(
                model=self.config.model_name,
                instructions=(request.system_prompt),
                input=(request.prompt_context.context + "\n\n" + request.user_prompt),
            )
        except OpenAIError as exc:
            logger.error(
                "generation.openai.failed",
                provider=self.provider.value,
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(f"OpenAI generation failed: {exc}") from exc

        duration = (perf_counter() - started) * 1000

        if response.usage is None:
            logger.error(
                "generation.openai.missing_usage",
                provider=self.provider.value,
                model=self.config.model_name,
            )
            raise GenerationExecutionError("OpenAI response did not include usage statistics")

        result = GenerationResult(
            request=request,
            execution=GenerationExecution(completed_at=datetime.now(UTC)),
            statistics=GenerationStatistics(
                provider=self.provider,
                model=self.config.model_name,
                latency_ms=duration,
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.total_tokens,
            ),
            provider=self.provider,
            model=self.config.model_name,
            content=response.output_text,
        )

        logger.info(
            "generation.openai.completed",
            provider=self.provider.value,
            model=self.config.model_name,
            latency_ms=duration,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
        )

        return result
