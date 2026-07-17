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
    get_list_field,
)


class EvidenceValidator(
    OutputValidatorInterface,
):
    """
    Checks a runtime output's evidence backs its claims (PRD §14): at
    least `minimum` evidence items, and each item carries non-empty
    `content` plus a source pointer (`citation_id` or `section_id`) —
    an evidence item with neither is unusable to a downstream consumer.

    `minimum` defaults to 0 so a contract that already enforces the
    count via `CompletenessValidator`'s `list_minimums` can compose
    this purely for the per-item structural checks without double
    -flagging the same missing-evidence condition.

    Runs only when `evidence` is present as a field at all.
    """

    def __init__(
        self,
        *,
        minimum: int = 0,
    ) -> None:
        self._minimum = minimum

    @property
    def name(
        self,
    ) -> str:
        return "runtime_evidence"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        payload = result.parsed_output

        if get_field(payload, "evidence") is None:
            return ValidatorOutcome()

        evidence_items = get_list_field(
            payload,
            "evidence",
        )

        issues: list[ValidationIssue] = []

        if len(evidence_items) < self._minimum:
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Runtime output has {len(evidence_items)} evidence item(s), "
                        f"needs at least {self._minimum}."
                    ),
                    details={
                        "minimum": self._minimum,
                        "actual": len(evidence_items),
                    },
                )
            )

        for index, item in enumerate(evidence_items):
            content = get_field(
                item,
                "content",
            )

            has_source = (
                get_field(item, "citation_id") is not None
                or get_field(item, "section_id") is not None
            )

            if not content or not has_source:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Evidence item {index} is missing content or a source "
                            "reference (citation_id/section_id)."
                        ),
                        details={
                            "index": index,
                        },
                    )
                )

        return ValidatorOutcome(
            issues=issues,
        )
