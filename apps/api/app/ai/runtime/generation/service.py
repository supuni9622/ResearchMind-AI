from __future__ import annotations

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.exceptions import (
    GenerationError,
    GenerationExecutionError,
    GenerationValidationError,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.registry import (
    GenerationRegistry,
)

logger = structlog.get_logger()


class GenerationService:
    def __init__(
        self,
        registry: GenerationRegistry,
    ):
        self._registry = registry

    async def generate(
        self,
        *,
        provider: GenerationProvider,
        request: GenerationRequest,
    ) -> GenerationResult:

        logger.info(
            "generation.requested",
            provider=provider.value,
            prompt_strategy=request.prompt_strategy.value,
            response_format=request.response_format.value,
        )

        self._validate(
            request,
        )

        generation_provider = self._registry.get(
            provider,
        )

        try:
            result = await generation_provider.generate(
                request,
            )
        except GenerationError:
            raise
        except Exception as exc:
            logger.error(
                "generation.unexpected_error",
                provider=provider.value,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise GenerationExecutionError(
                f"Generation failed unexpectedly for provider '{provider}'."
            ) from exc

        logger.info(
            "generation.completed",
            provider=provider.value,
            model=result.model,
            latency_ms=result.statistics.latency_ms,
            prompt_tokens=result.statistics.prompt_tokens,
            completion_tokens=result.statistics.completion_tokens,
            total_tokens=result.statistics.total_tokens,
        )

        return result

    @staticmethod
    def _validate(
        request: GenerationRequest,
    ) -> None:

        if not request.user_prompt.strip():
            logger.warning(
                "generation.validation_failed",
                reason="empty_user_prompt",
            )
            raise (GenerationValidationError("Prompt cannot be empty."))

        if not request.prompt_context.context:
            logger.warning(
                "generation.validation_failed",
                reason="empty_prompt_context",
            )
            raise (GenerationValidationError("Prompt context cannot be empty."))
