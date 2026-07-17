from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.fields import (
    get_field,
)

_DEFAULT_MIN_SUMMARY_LENGTH = 20
"""Chars. Guards against trivial one-word/one-line summaries (PRD §15 "Minimum Length")."""


class CompletenessValidator(
    OutputValidatorInterface,
):
    """
    Checks a runtime output isn't empty or trivial (PRD §14):
    scalar `required_fields` must be present and non-empty, list-typed
    fields in `list_minimums` must meet their minimum item count, and
    `summary` (when required) must clear a minimum length.

    Configured per contract rather than hard-coded, since required
    fields differ by `RuntimeType` (PRD §15-§19) — e.g. the Research
    Runtime Contract requires `sections`/`citations`/`evidence` with
    minimums of 2/1/1.
    """

    def __init__(
        self,
        *,
        required_fields: list[str] | None = None,
        list_minimums: dict[str, int] | None = None,
        min_summary_length: int = _DEFAULT_MIN_SUMMARY_LENGTH,
    ) -> None:
        self._required_fields = required_fields or []

        self._list_minimums = list_minimums or {}

        self._min_summary_length = min_summary_length

    @property
    def name(
        self,
    ) -> str:
        return "runtime_completeness"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        payload = result.parsed_output

        issues: list[ValidationIssue] = []

        for field_name in self._required_fields:
            value = get_field(
                payload,
                field_name,
            )

            if value in (None, ""):
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=f"Runtime output is missing required field '{field_name}'.",
                        details={
                            "field": field_name,
                        },
                    )
                )

        for field_name, minimum in self._list_minimums.items():
            value = get_field(
                payload,
                field_name,
            )

            actual = len(value) if isinstance(value, list) else 0

            if actual < minimum:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Runtime output has {actual} '{field_name}' item(s), "
                            f"needs at least {minimum}."
                        ),
                        details={
                            "field": field_name,
                            "minimum": minimum,
                            "actual": actual,
                        },
                    )
                )

        summary = get_field(
            payload,
            "summary",
        )

        if (
            "summary" in self._required_fields
            and isinstance(summary, str)
            and 0 < len(summary.strip()) < self._min_summary_length
        ):
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Runtime output summary is only {len(summary.strip())} chars — "
                        "likely too trivial to be useful."
                    ),
                    details={
                        "min_length": self._min_summary_length,
                    },
                )
            )

        return ValidatorOutcome(
            issues=issues,
        )
