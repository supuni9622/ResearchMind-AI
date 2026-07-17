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
    get_list_field,
    item_id,
)


class RuntimeCitationValidator(
    OutputValidatorInterface,
):
    """
    Checks that a runtime output's structured `citations`/`evidence`
    fields reference citations actually present in the retrieved
    context (PRD §14) — the structured-output counterpart to
    `output.citation_validator.CitationValidator`, which only checks
    bracketed markers (e.g. "[S1]") in free-text `content`.

    Runs only when the prompt context carries known citations and the
    output has structured citation/evidence fields referencing any —
    an output with nothing to cite is left alone, same as
    `CitationValidator`.
    """

    @property
    def name(
        self,
    ) -> str:
        return "runtime_citation"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        prompt_context = result.request.prompt_context

        known_ids = {citation.citation_id for citation in prompt_context.citations}

        known_ids |= {chunk.citation_id for chunk in prompt_context.chunks if chunk.citation_id}

        if not known_ids:
            return ValidatorOutcome()

        payload = result.parsed_output

        referenced_ids: set[str] = set()

        for citation in get_list_field(payload, "citations"):
            citation_id = item_id(
                citation,
                "citation_id",
                "id",
            )

            if citation_id is not None:
                referenced_ids.add(
                    citation_id,
                )

        for evidence in get_list_field(payload, "evidence"):
            citation_id = item_id(
                evidence,
                "citation_id",
            )

            if citation_id is not None:
                referenced_ids.add(
                    citation_id,
                )

        if not referenced_ids:
            return ValidatorOutcome()

        unknown_ids = sorted(
            referenced_ids - known_ids,
        )

        if not unknown_ids:
            return ValidatorOutcome()

        return ValidatorOutcome(
            issues=[
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Runtime output references source(s) not present in the "
                        f"retrieved context: {', '.join(unknown_ids)}"
                    ),
                    details={
                        "unknown_citations": unknown_ids,
                        "known_citations": sorted(
                            known_ids,
                        ),
                    },
                )
            ],
        )
