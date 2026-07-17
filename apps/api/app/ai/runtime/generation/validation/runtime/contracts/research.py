from __future__ import annotations

from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.contracts.base import (
    BaseRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)
from app.ai.runtime.generation.validation.runtime.validators.citation import (
    RuntimeCitationValidator,
)
from app.ai.runtime.generation.validation.runtime.validators.completeness import (
    CompletenessValidator,
)
from app.ai.runtime.generation.validation.runtime.validators.confidence import (
    ConfidenceValidator,
)
from app.ai.runtime.generation.validation.runtime.validators.consistency import (
    ConsistencyValidator,
)
from app.ai.runtime.generation.validation.runtime.validators.evidence import (
    EvidenceValidator,
)

_MIN_SECTIONS = 2
_MIN_CITATIONS = 1
_MIN_EVIDENCE = 1
_MIN_SUMMARY_LENGTH = 40


class ResearchRuntimeContract(
    BaseRuntimeContract,
):
    """
    Research Runtime Contract (PRD §15) — the first concrete runtime
    contract. Requires a non-trivial `summary`, at least 2 `sections`,
    at least 1 `citation`, at least 1 `evidence` item, and a
    `confidence` score in `[0, 1]` on `GenerationResult.parsed_output`.

    Entirely composed from the generic runtime validators (PRD §14) —
    `EvidenceValidator`'s own count check is disabled (`minimum=0`)
    since `CompletenessValidator`'s `list_minimums` already enforces
    the evidence-count requirement; composing both would double-flag
    the same missing-evidence condition.
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "summary",
                    "confidence",
                ],
                list_minimums={
                    "sections": _MIN_SECTIONS,
                    "citations": _MIN_CITATIONS,
                    "evidence": _MIN_EVIDENCE,
                },
                min_summary_length=_MIN_SUMMARY_LENGTH,
            ),
            ConsistencyValidator(),
            EvidenceValidator(
                minimum=0,
            ),
            RuntimeCitationValidator(),
            ConfidenceValidator(),
        ]

    @property
    def runtime(
        self,
    ) -> RuntimeType:
        return RuntimeType.RESEARCH

    @property
    def contract_name(
        self,
    ) -> str:
        return "research_contract"

    @property
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._checks,
        )
