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
from groq import AsyncGroq, GroqError

logger = structlog.get_logger()


class GroqProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(config)

        self._client = AsyncGroq(
            api_key=settings.groq_api_key,
        )

    @property
    def provider(
        self,
    ):
        return GenerationProvider.GROQ

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = perf_counter()

        logger.info(
            "generation.groq.started",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        try:
            response = await self._client.chat.completions.create(
                model=self.config.model_name,
                temperature=self.config.temperature,
                max_completion_tokens=self.config.max_tokens,
                messages=[
                    {
                        "role": "system",
                        "content": (request.system_prompt or ""),
                    },
                    {
                        "role": "user",
                        "content": (request.prompt_context.context + "\n\n" + request.user_prompt),
                    },
                ],
            )
        except GroqError as exc:
            logger.error(
                "generation.groq.failed",
                provider=self.provider.value,
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(f"Groq generation failed: {exc}") from exc

        duration = (perf_counter() - started) * 1000

        if response.usage is None:
            logger.error(
                "generation.groq.missing_usage",
                provider=self.provider.value,
                model=self.config.model_name,
            )
            raise GenerationExecutionError("Groq response did not include usage statistics")

        result = GenerationResult(
            request=request,
            execution=GenerationExecution(completed_at=datetime.now(UTC)),
            statistics=GenerationStatistics(
                provider=self.provider,
                model=self.config.model_name,
                latency_ms=duration,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
            provider=self.provider,
            model=self.config.model_name,
            content=response.choices[0].message.content or "",
            finish_reason=response.choices[0].finish_reason,
        )

        logger.info(
            "generation.groq.completed",
            provider=self.provider.value,
            model=self.config.model_name,
            latency_ms=duration,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
            finish_reason=result.finish_reason,
        )

        return result
