from __future__ import annotations

from app.ai.knowledge.context.citations.validity import (
    check_prompt_context_citation_validity,
)
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


class CitationValidator(
    OutputValidatorInterface,
):
    """
    Checks that citation markers in `GenerationResult.content` refer to
    sources actually present in `request.prompt_context` — catching
    fabricated citations the model invented rather than grounded them
    in retrieved context.

    Only runs when the prompt context actually carries known citations;
    generations with nothing to cite are left alone (an arbitrary
    bracketed token, e.g. a JSON array literal, is not evidence of a
    fabricated citation on its own).

    Delegates to `check_prompt_context_citation_validity`
    (`knowledge/context/citations/validity.py`), the shared,
    cross-surface citation-validity checker generalized from this
    validator and `review_draft()`'s existence check (EVALUATION_PLAN.md
    §8) — this validator surfaces only the existence result as a
    blocking issue, matching its prior behavior exactly; the richer
    syntax/fabrication-rate/provenance checks that function also computes
    are for the non-blocking, post-hoc cross-surface report, not this
    live validation gate.
    """

    @property
    def name(
        self,
    ) -> str:
        return "citation"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        report = check_prompt_context_citation_validity(
            content=result.content,
            prompt_context=result.request.prompt_context,
        )

        if not report.unknown_citation_ids:
            return ValidatorOutcome()

        return ValidatorOutcome(
            issues=[
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Response cites source(s) not present in the retrieved "
                        f"context: {', '.join(report.unknown_citation_ids)}"
                    ),
                    details={
                        "unknown_citations": report.unknown_citation_ids,
                        "known_citations": report.known_citation_ids,
                    },
                )
            ],
        )
