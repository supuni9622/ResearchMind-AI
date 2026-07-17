from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)

import structlog
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.orchestration.context import (
    GenerationExecutionContext,
)
from app.ai.runtime.generation.orchestration.interfaces import (
    GenerationRuntimeInterface,
)
from app.ai.runtime.generation.orchestration.state import (
    GenerationExecutionState,
)
from app.ai.runtime.generation.service import (
    GenerationService,
)

logger = structlog.get_logger()


class GenerationRuntime(
    GenerationRuntimeInterface,
):
    """
    The Generation Runtime Platform's orchestrator (PRD §6/§7).

    Deliberately thin: every stage in the frozen ordering (input
    validation, input guardrails, prompt registry, routing, cache
    lookup, provider execution, structured outputs, generation
    guardrails, output validation, runtime validation, metrics,
    artifacts) already lives inside `GenerationService.generate()` --
    see the Generation/Validation/Guardrails/Routing/Runtime Caching/
    Metrics/Artifact platforms this milestone only orchestrates (PRD §5).

    This class does not re-implement or reorder any of that. It owns
    exactly what the PRD assigns to the runtime layer and nothing the
    underlying platforms already own: minting a `GenerationExecutionContext`
    (trace id, timing) up front, delegating the actual execution to
    `GenerationService`, and folding the result (or failure) back into
    that context/a `GenerationExecutionState` for tracing -- see §7
    "Generation Runtime does NOT own: provider execution, planning,
    workflows, agent state, retrieval, reasoning loops, checkpoints."
    """

    def __init__(
        self,
        generation_service: GenerationService,
    ) -> None:

        self._generation_service = generation_service

    async def execute(
        self,
        request: GenerationRequest,
        *,
        provider: GenerationProvider | None = None,
    ) -> GenerationResult:

        context = GenerationExecutionContext.for_request(
            request,
        )

        state = GenerationExecutionState(
            context=context,
            request=request,
        )

        log = logger.bind(
            trace_id=str(context.trace_id),
            request_id=str(context.request_id),
            runtime=(context.runtime.value if context.runtime else None),
        )

        log.info(
            "generation_runtime.started",
        )

        try:
            result = await self._generation_service.generate(
                request=request,
                provider=provider,
            )
        except Exception as exc:
            state.failed = True

            state.exception = exc

            context.completed_at = datetime.now(
                UTC,
            )

            log.error(
                "generation_runtime.failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )

            raise

        state.result = result

        context.finalize(
            result,
        )

        log.info(
            "generation_runtime.completed",
            provider=(context.provider.value if context.provider else None),
            latency_ms=result.statistics.latency_ms,
            regeneration_attempts=result.regeneration_attempts,
        )

        return result
