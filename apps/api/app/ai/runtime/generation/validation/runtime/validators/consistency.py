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
    Checks referential integrity between a source list field (default
    `sections`) and a referencing list field (default `evidence`) on a
    runtime output (PRD §14) — a referencing item naming an id via
    `ref_key` must point at a source item that actually exists, or it's
    an orphan reference.

    Field names are configurable (default to the Research Runtime
    Contract's `sections`/`evidence`/`section_id`, its original fixed
    behavior) so other contracts can reuse this same referential-
    integrity check against their own list-shaped fields (e.g. the MCP
    Runtime Contract's `tool_outputs`/`tool_references`) instead of
    each writing a bespoke version of the same loop.

    Runs only when both list fields are present and at least one
    source item carries an identifiable id — outputs without that
    structure have nothing to check.
    """

    def __init__(
        self,
        *,
        list_field: str = "sections",
        id_keys: tuple[str, ...] = (
            "id",
            "section_id",
        ),
        ref_list_field: str = "evidence",
        ref_key: str = "section_id",
    ) -> None:
        self._list_field = list_field

        self._id_keys = id_keys

        self._ref_list_field = ref_list_field

        self._ref_key = ref_key

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

        source_items = get_list_field(
            payload,
            self._list_field,
        )

        ref_items = get_list_field(
            payload,
            self._ref_list_field,
        )

        if not source_items or not ref_items:
            return ValidatorOutcome()

        known_ids = {
            source_id
            for item in source_items
            if (
                source_id := item_id(
                    item,
                    *self._id_keys,
                )
            )
            is not None
        }

        if not known_ids:
            return ValidatorOutcome()

        issues: list[ValidationIssue] = []

        for index, ref_item in enumerate(ref_items):
            ref_value = get_field(
                ref_item,
                self._ref_key,
            )

            if ref_value is not None and ref_value not in known_ids:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"{self._ref_list_field} item {index} references an "
                            f"unknown '{self._list_field}' id: '{ref_value}'."
                        ),
                        details={
                            "index": index,
                            self._ref_key: ref_value,
                            "known_ids": sorted(
                                known_ids,
                            ),
                        },
                    )
                )

        return ValidatorOutcome(
            issues=issues,
        )
