from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.orchestration.context import (
    GenerationExecutionContext,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class GenerationExecutionState(
    BaseModel,
):
    """
    In-flight state for one `execute_generation()` call (PRD §10).

    Exists so a future LangGraph node can hold and inspect a single
    object across the call rather than threading context/result/failure
    as separate values -- this platform does not itself branch on
    `failed`/`exception`, `GenerationRuntime.execute()` re-raises instead
    (see orchestrator.py).
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
    )

    context: GenerationExecutionContext

    request: GenerationRequest

    result: GenerationResult | None = None

    failed: bool = False

    exception: BaseException | None = None
