from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)
from typing import Any
from uuid import UUID, uuid4

from app.ai.guardrails.models import (
    GuardrailReport,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.validation.models import (
    ValidationReport,
)
from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class GenerationExecutionContext(
    BaseModel,
):
    """
    Canonical runtime metadata for one `execute_generation()` call (PRD
    §9). Owned by the Generation Runtime Platform, not by any individual
    platform it orchestrates -- `GenerationService` itself remains
    unaware this wraps it.

    `trace_id` is this platform's own tracing identifier, minted fresh
    per execution regardless of `request_id` (which the caller controls
    and may reuse across regeneration/retry layers upstream). It is
    distinct from `langsmith_trace_id`/`langgraph_run_id` below, which
    identify the *same* execution in external systems once those
    integrations exist.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    request_id: UUID

    runtime: RuntimeType | None = None

    session_id: UUID | None = None

    trace_id: UUID = Field(
        default_factory=uuid4,
    )

    start_time: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    completed_at: datetime | None = None

    provider: GenerationProvider | None = None

    routing_decision: dict[str, Any] | None = None
    """
    Mirrors `GenerationResult.metadata["routing"]` (see
    `GenerationService._routing_metadata`) -- a summary dict, not the
    full `RoutingDecision`, since that's all `generate()` preserves past
    the routing call itself.
    """

    cache_decision: dict[str, Any] | None = None
    """Mirrors `GenerationResult.metadata["cache"]`."""

    validation_report: ValidationReport | None = None

    guardrail_report: GuardrailReport | None = None

    artifact_metadata: dict[str, Any] | None = None
    """
    Which `ArtifactRuntime` this execution was tagged with for the
    Artifact Platform's policy resolution. Records intent, not
    confirmation -- actual persistence is best-effort and failures are
    swallowed by `GenerationService` itself (see
    `_persist_generation_artifact`), so a populated value here does not
    guarantee the artifact was written.
    """

    langsmith_trace_id: str | None = None
    """Reserved (PRD §14) -- no LangSmith integration exists yet."""

    langgraph_run_id: str | None = None
    """Reserved (PRD §15) -- no LangGraph-based runtime exists yet."""

    @classmethod
    def for_request(
        cls,
        request: GenerationRequest,
    ) -> GenerationExecutionContext:

        return cls(
            request_id=request.request_id,
            runtime=request.runtime,
            session_id=request.session_id,
            artifact_metadata=(
                {"runtime": request.artifact_runtime.value} if request.artifact_runtime else None
            ),
        )

    def finalize(
        self,
        result: GenerationResult,
    ) -> None:
        """
        Populates the fields only known once `GenerationService.generate()`
        has returned -- mutates in place since the context is held by the
        in-flight `GenerationExecutionState`, not rebuilt.
        """

        self.completed_at = datetime.now(UTC)

        self.provider = result.provider

        self.routing_decision = result.metadata.get(
            "routing",
        )

        self.cache_decision = result.metadata.get(
            "cache",
        )

        self.validation_report = result.validation

        self.guardrail_report = result.guardrails
