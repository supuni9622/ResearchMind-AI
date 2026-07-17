from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from app.ai.observability.timer import Timer
from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.aggregation import (
    aggregate_outcomes,
    crash_outcome,
)
from app.ai.runtime.generation.validation.models import (
    ValidationResult,
    ValidationStage,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.registry import (
    RuntimeRegistry,
)

logger = structlog.get_logger()


class RuntimeValidationService:
    """
    Coordinates execution of the runtime stage (PRD §8, §13): resolves
    `GenerationResult.request.runtime`, runs that runtime's registered
    contract plus any standalone validators, and aggregates the result
    into a `ValidationResult` — the same shape `ValidationService` uses
    for the input/output/hallucination stages.

    Requests with no `runtime` set (the common case today — see
    `GenerationRequest.runtime`) skip this stage entirely: there's no
    contract to resolve, so the result is trivially valid with no
    score, matching how the other stages behave when nothing is
    registered for them.
    """

    def __init__(
        self,
        registry: RuntimeRegistry,
    ) -> None:
        self._registry = registry

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidationResult:

        runtime = result.request.runtime

        if runtime is None:
            return ValidationResult(
                valid=True,
                issues=[],
                score=None,
            )

        logger.info(
            "runtime.validation.started",
            runtime=runtime.value,
            generation_id=str(result.generation_id),
        )

        timer = Timer()
        timer.start()

        outcomes: list[ValidatorOutcome] = []

        contract = self._registry.contract_for(
            runtime,
        )

        if contract is not None:
            outcomes.append(
                await self._safe_validate(
                    name=f"{runtime.value}_contract",
                    result=result,
                    validate=contract.validate,
                )
            )

        for validator in self._registry.validators_for(
            runtime,
        ):
            outcomes.append(
                await self._safe_validate(
                    name=validator.name,
                    result=result,
                    validate=validator.validate,
                )
            )

        validation_result = aggregate_outcomes(
            stage=ValidationStage.RUNTIME,
            outcomes=outcomes,
        )

        timer.stop()

        log_event = (
            "runtime.validation.completed"
            if validation_result.valid
            else "runtime.validation.failed"
        )

        logger.info(
            log_event,
            runtime=runtime.value,
            generation_id=str(result.generation_id),
            duration_ms=timer.elapsed_milliseconds,
            score=validation_result.score,
            valid=validation_result.valid,
            issue_count=len(validation_result.issues),
        )

        return validation_result

    @staticmethod
    async def _safe_validate(
        *,
        name: str,
        result: GenerationResult,
        validate: Callable[[GenerationResult], Awaitable[ValidatorOutcome]],
    ) -> ValidatorOutcome:
        try:
            return await validate(
                result,
            )
        except Exception as exc:
            return crash_outcome(
                validator_name=name,
                stage=ValidationStage.RUNTIME,
                exc=exc,
            )
