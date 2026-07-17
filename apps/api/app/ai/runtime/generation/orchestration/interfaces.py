from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)


class GenerationRuntimeInterface(
    ABC,
):
    """
    Canonical contract for the Generation Runtime Platform's single
    entrypoint (PRD §11). Research/Planner/Reviewer/Agent/MCP runtimes
    depend on this, not on `GenerationService` directly -- see
    `generation_runtime_platform_prd.md` §7/§8.
    """

    @abstractmethod
    async def execute(
        self,
        request: GenerationRequest,
        *,
        provider: GenerationProvider | None = None,
    ) -> GenerationResult:
        pass
