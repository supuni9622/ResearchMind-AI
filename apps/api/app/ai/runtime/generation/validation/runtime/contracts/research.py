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

_MIN_FINDINGS = 2
_MIN_CITATION_IDS = 1


class ResearchRuntimeContract(
    BaseRuntimeContract,
):
    """
    Research Runtime Contract (PRD §15) — the first concrete runtime
    contract. Requires a non-empty `abstract`, at least 2 `findings`
    sections, and at least 1 cited source id on `GenerationResult.
    parsed_output`. Field names mirror `ResearchDraft`/
    `ResearchDraftSection` (`app/ai/runtime/research/synthesis/models.py`),
    the actual `output_model` the synthesis step requests -- that
    schema has no `confidence`/`evidence` concept, so unlike the
    original PRD §15 sketch there's nothing for `ConfidenceValidator`/
    `EvidenceValidator`/`ConsistencyValidator` to check; they're kept
    here as safe no-ops (each only runs when its target field is
    present at all) in case a future schema revision adds one.
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "abstract",
                ],
                list_minimums={
                    "findings": _MIN_FINDINGS,
                    "citation_ids": _MIN_CITATION_IDS,
                },
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
