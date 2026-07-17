"""
Generation Runtime Platform composition root (PRD §17).

`create_generation_runtime()`'s listed responsibilities --
ValidationService, GuardrailService, RoutingService, CacheService,
MetricsService, ArtifactService, GenerationService -- are exactly what
`create_generation_service()` (generation/create.py) already assembles.
Re-implementing that wiring here would duplicate the entire provider
registry / service construction a second time for no behavioral
difference, so this composition root builds on top of it instead of
alongside it.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from app.ai.runtime.generation.create import (
    create_generation_service,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.orchestration.orchestrator import (
    GenerationRuntime,
)

logger = structlog.get_logger()


def create_generation_runtime() -> GenerationRuntime:
    """
    Create a fully configured GenerationRuntime.
    """

    return GenerationRuntime(
        generation_service=create_generation_service(),
    )


@lru_cache
def get_generation_runtime() -> GenerationRuntime:

    runtime = create_generation_runtime()

    logger.info(
        "generation_runtime.initialized",
    )

    return runtime


async def execute_generation(
    request: GenerationRequest,
    *,
    provider: GenerationProvider | None = None,
) -> GenerationResult:
    """
    The canonical Generation Runtime Platform entrypoint (PRD §11).

    Research/Planner/Reviewer/Agent/MCP runtimes -- and any future
    LangGraph-based runtime (PRD §15) -- should call this instead of
    `GenerationService.generate()` directly, setting `request.runtime`
    to identify which runtime is calling (PRD §8: "Generation Runtime
    never decides runtime. Caller owns runtime."). `provider` is an
    optional explicit override (e.g. admin/debug tooling) forwarded
    straight through to `GenerationService.generate()` -- routing still
    resolves it from `request.routing_strategy` when left `None`.
    """

    return await get_generation_runtime().execute(
        request,
        provider=provider,
    )
