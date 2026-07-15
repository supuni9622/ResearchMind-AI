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
from google import genai
from google.genai.errors import APIError

logger = structlog.get_logger()


class GeminiProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(config)

        self._client = genai.Client(
            api_key=settings.gemini_api_key,
        )

    @property
    def provider(
        self,
    ):
        return GenerationProvider.GEMINI

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = perf_counter()

        logger.info(
            "generation.gemini.started",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        try:
            response = await self._client.aio.models.generate_content(
                model=self.config.model_name,
                contents=(request.prompt_context.context + "\n\n" + request.user_prompt),
            )
        except APIError as exc:
            logger.error(
                "generation.gemini.failed",
                provider=self.provider.value,
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(f"Gemini generation failed: {exc}") from exc

        duration = (perf_counter() - started) * 1000

        usage = response.usage_metadata

        result = GenerationResult(
            request=request,
            execution=GenerationExecution(completed_at=datetime.now(UTC)),
            statistics=GenerationStatistics(
                provider=self.provider,
                model=self.config.model_name,
                latency_ms=duration,
                prompt_tokens=(usage.prompt_token_count or 0) if usage else 0,
                completion_tokens=(usage.candidates_token_count or 0) if usage else 0,
                total_tokens=(usage.total_token_count or 0) if usage else 0,
            ),
            provider=self.provider,
            model=self.config.model_name,
            content=response.text or "",
        )

        logger.info(
            "generation.gemini.completed",
            provider=self.provider.value,
            model=self.config.model_name,
            latency_ms=duration,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
        )

        return result
