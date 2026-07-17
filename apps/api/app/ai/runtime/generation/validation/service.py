from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationRequest,
    GenerationResult,
)
from app.ai.runtime.generation.validation.aggregation import (
    aggregate_outcomes,
    crash_outcome,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationReport,
    ValidationResult,
    ValidationStage,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.registry import (
    ValidationRegistry,
)
from app.ai.runtime.generation.validation.runtime.service import (
    RuntimeValidationService,
)
from app.ai.runtime.generation.validation.scoring import (
    compute_overall_score,
)


class ValidationService:
    """
    Full Validation flow (PRD §14): input -> output -> hallucination ->
    report. Each stage can also be run independently — `GenerationService`
    only needs `validate()`, but other runtimes may want a single stage
    (e.g. an agent runtime checking only its own output).
    """

    def __init__(
        self,
        registry: ValidationRegistry,
    ) -> None:
        self._registry = registry

        self._runtime_validation_service = RuntimeValidationService(
            registry.runtime_registry,
        )

    @property
    def validator_names(
        self,
    ) -> list[str]:
        return [
            *(validator.name for validator in self._registry.input_validators),
            *(validator.name for validator in self._registry.output_validators),
            *(validator.name for validator in self._registry.hallucination_validators),
            *(validator.name for validator in self._registry.runtime_validators),
        ]

    # ==========================================================
    # Per-stage
    # ==========================================================

    async def validate_input(
        self,
        request: GenerationRequest,
        context: InputValidationContext | None = None,
    ) -> ValidationResult:

        context = context or InputValidationContext()

        outcomes: list[ValidatorOutcome] = []

        for validator in self._registry.input_validators:
            try:
                outcomes.append(
                    await validator.validate(
                        request,
                        context,
                    )
                )
            except Exception as exc:
                outcomes.append(
                    crash_outcome(
                        validator_name=validator.name,
                        stage=ValidationStage.INPUT,
                        exc=exc,
                    )
                )

        return aggregate_outcomes(
            stage=ValidationStage.INPUT,
            outcomes=outcomes,
        )

    async def validate_output(
        self,
        result: GenerationResult,
    ) -> ValidationResult:

        return await self._validate_result_stage(
            stage=ValidationStage.OUTPUT,
            validators=self._registry.output_validators,
            result=result,
        )

    async def validate_hallucination(
        self,
        result: GenerationResult,
    ) -> ValidationResult:

        return await self._validate_result_stage(
            stage=ValidationStage.HALLUCINATION,
            validators=self._registry.hallucination_validators,
            result=result,
        )

    async def validate_runtime(
        self,
        result: GenerationResult,
    ) -> ValidationResult:

        return await self._runtime_validation_service.validate(
            result,
        )

    # ==========================================================
    # Full report
    # ==========================================================

    async def validate(
        self,
        *,
        request: GenerationRequest,
        result: GenerationResult,
        context: InputValidationContext | None = None,
    ) -> ValidationReport:

        input_validation = await self.validate_input(
            request,
            context,
        )

        output_validation = await self.validate_output(
            result,
        )

        hallucination_validation = await self.validate_hallucination(
            result,
        )

        runtime_validation = await self.validate_runtime(
            result,
        )

        overall_score = compute_overall_score(
            input_score=input_validation.score,
            output_score=output_validation.score,
            hallucination_score=hallucination_validation.score,
            runtime_score=runtime_validation.score,
        )

        valid = (
            input_validation.valid
            and output_validation.valid
            and hallucination_validation.valid
            and runtime_validation.valid
        )

        return ValidationReport(
            input_validation=input_validation,
            output_validation=output_validation,
            hallucination_validation=hallucination_validation,
            runtime_validation=runtime_validation,
            overall_score=overall_score,
            valid=valid,
        )

    # ==========================================================
    # Internal
    # ==========================================================

    async def _validate_result_stage(
        self,
        *,
        stage: ValidationStage,
        validators: list[OutputValidatorInterface],
        result: GenerationResult,
    ) -> ValidationResult:

        outcomes: list[ValidatorOutcome] = []

        for validator in validators:
            try:
                outcomes.append(
                    await validator.validate(
                        result,
                    )
                )
            except Exception as exc:
                outcomes.append(
                    crash_outcome(
                        validator_name=validator.name,
                        stage=stage,
                        exc=exc,
                    )
                )

        return aggregate_outcomes(
            stage=stage,
            outcomes=outcomes,
        )
