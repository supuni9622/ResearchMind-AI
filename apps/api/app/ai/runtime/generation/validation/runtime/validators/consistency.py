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
    item_id,
)


class ConsistencyValidator(
    OutputValidatorInterface,
):
    """
    Checks referential integrity between an output's `evidence` items
    and its `sections` (PRD §14) — an evidence item naming a
    `section_id` must reference a section that actually exists, or it's
    an orphan reference.

    Runs only when both `sections` and `evidence` are present as lists
    and at least one section carries an identifiable id — outputs
    without that structure have nothing to check.
    """

    @property
    def name(
        self,
    ) -> str:
        return "runtime_consistency"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        payload = result.parsed_output

        sections = get_list_field(
            payload,
            "sections",
        )

        evidence_items = get_list_field(
            payload,
            "evidence",
        )

        if not sections or not evidence_items:
            return ValidatorOutcome()

        known_section_ids = {
            section_id
            for item in sections
            if (
                section_id := item_id(
                    item,
                    "id",
                    "section_id",
                )
            )
            is not None
        }

        if not known_section_ids:
            return ValidatorOutcome()

        issues: list[ValidationIssue] = []

        for index, evidence in enumerate(evidence_items):
            section_ref = get_field(
                evidence,
                "section_id",
            )

            if section_ref is not None and section_ref not in known_section_ids:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Evidence item {index} references unknown section '{section_ref}'."
                        ),
                        details={
                            "index": index,
                            "section_id": section_ref,
                            "known_sections": sorted(
                                known_section_ids,
                            ),
                        },
                    )
                )

        return ValidatorOutcome(
            issues=issues,
        )
