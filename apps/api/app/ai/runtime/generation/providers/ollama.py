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
from ollama import AsyncClient, RequestError, ResponseError

logger = structlog.get_logger()


class OllamaProvider(
    BaseGenerationProvider,
):
    def __init__(
        self,
        config,
    ):
        super().__init__(config)

        self._client = AsyncClient(
            host=settings.ollama_host,
        )

    @property
    def provider(
        self,
    ):
        return GenerationProvider.OLLAMA

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:

        started = perf_counter()

        logger.info(
            "generation.ollama.started",
            provider=self.provider.value,
            model=self.config.model_name,
        )

        try:
            response = await self._client.chat(
                model=self.config.model_name,
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
        except (RequestError, ResponseError, ConnectionError) as exc:
            logger.error(
                "generation.ollama.failed",
                provider=self.provider.value,
                model=self.config.model_name,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(f"Ollama generation failed: {exc}") from exc

        duration = (perf_counter() - started) * 1000

        result = GenerationResult(
            request=request,
            execution=GenerationExecution(completed_at=datetime.now(UTC)),
            statistics=GenerationStatistics(
                provider=self.provider,
                model=self.config.model_name,
                latency_ms=duration,
                prompt_tokens=response.prompt_eval_count or 0,
                completion_tokens=response.eval_count or 0,
                total_tokens=(response.prompt_eval_count or 0) + (response.eval_count or 0),
            ),
            provider=self.provider,
            model=self.config.model_name,
            content=response.message.content or "",
        )

        logger.info(
            "generation.ollama.completed",
            provider=self.provider.value,
            model=self.config.model_name,
            latency_ms=duration,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
        )

        return result
