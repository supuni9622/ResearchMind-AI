from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ValidationSeverity(StrEnum):
    ERROR = "error"

    WARNING = "warning"


class ValidationStage(StrEnum):
    INPUT = "input"

    OUTPUT = "output"

    HALLUCINATION = "hallucination"

    RUNTIME = "runtime"
    """
    Reserved for the future per-runtime contract validators (PRD §11) —
    no validator populates this stage yet, so `ValidationReport.runtime_validation`
    is always `None` today.
    """


class ValidationIssue(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    validator: str

    stage: ValidationStage = ValidationStage.OUTPUT
    """
    Which validation stage produced this issue. Individual validators do
    not need to set this themselves — `ValidationService` stamps the
    correct stage when it aggregates each category's issues, so the
    default here only matters for issues constructed outside that path
    (e.g. directly in tests).
    """

    severity: ValidationSeverity

    message: str

    details: dict[str, Any] = Field(
        default_factory=dict,
    )


class ValidatorOutcome(
    BaseModel,
):
    """
    What a single validator returns from `validate()`.

    `score` is optional — most validators only surface pass/fail via
    `issues` (e.g. schema/citation checks), while a few (token budget,
    JSON parseability, groundedness) have a meaningful continuous score
    to contribute toward `ValidationResult.score` / the overall
    weighted formula (PRD §15). Validators with nothing to check
    against (no schema, no context) should return an empty outcome
    rather than erroring — see `OutputValidatorInterface`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    issues: list[ValidationIssue] = Field(
        default_factory=list,
    )

    score: float | None = None


class InputValidationContext(
    BaseModel,
):
    """
    Provider-derived facts an input validator may need but that don't
    live on `GenerationRequest` itself (it describes what's being
    asked for, not what the resolved provider can actually do).

    Deliberately plain primitives rather than `ProviderCapabilities` /
    `BaseGenerationConfig` — those live in `generation/models.py`, which
    already imports from `validation/models.py`; depending on them here
    would create an import cycle.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    context_window: int | None = None

    supports_streaming: bool | None = None

    supports_structured_output: bool | None = None

    supports_json_mode: bool | None = None

    supports_tool_calling: bool | None = None


class ValidationResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    valid: bool

    issues: list[ValidationIssue] = Field(
        default_factory=list,
    )

    score: float | None = None
    """
    Average of every contributing validator's `ValidatorOutcome.score`
    in this stage; `None` when none of them produced one.
    """


class ValidationReport(
    BaseModel,
):
    """
    Aggregated, multi-stage validation outcome for a single generation
    (PRD §7). Replaces the single-stage `ValidationResult` that used to
    sit on `GenerationResult.validation`.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    input_validation: ValidationResult

    output_validation: ValidationResult

    hallucination_validation: ValidationResult

    runtime_validation: ValidationResult | None = None

    overall_score: float | None = None

    valid: bool
    """
    `True` only when every stage that ran is itself valid (no ERROR
    issues). Note `GenerationService`'s regeneration policy does not use
    this field directly — it only reacts to `output_validation.valid`,
    since input-stage issues describe the *request* and re-generating
    the same request wouldn't fix them. This field is for downstream
    consumers (Artifacts, Evaluation) that want a single yes/no signal.
    """

    @property
    def issues(
        self,
    ) -> list[ValidationIssue]:
        """
        Every issue across every stage that ran, in stage order
        (input, output, hallucination, runtime).
        """

        all_issues = [
            *self.input_validation.issues,
            *self.output_validation.issues,
            *self.hallucination_validation.issues,
        ]

        if self.runtime_validation is not None:
            all_issues.extend(
                self.runtime_validation.issues,
            )

        return all_issues
