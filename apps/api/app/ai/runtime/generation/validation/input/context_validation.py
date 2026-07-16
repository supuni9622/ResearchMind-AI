from __future__ import annotations

from collections import Counter

from app.ai.knowledge.context.models import (
    ContextChunk,
    PromptContext,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)
from app.ai.runtime.generation.validation.interfaces import (
    InputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    InputValidationContext,
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)


class ContextValidator(
    InputValidatorInterface,
):
    """
    Data-quality checks on `request.prompt_context` — empty chunks,
    duplicate chunks, and citation/chunk metadata consistency.

    These are all data-quality signals about upstream retrieval/context
    construction, not generation-time failures, so every issue here is
    a WARNING: none of them should block or gate a generation the way
    `GenerationService._validate()`'s "context is completely empty"
    hard check does.
    """

    @property
    def name(
        self,
    ) -> str:
        return "context"

    async def validate(
        self,
        request: GenerationRequest,
        context: InputValidationContext,
    ) -> ValidatorOutcome:

        prompt_context = request.prompt_context

        issues: list[ValidationIssue] = []

        issues.extend(
            self._empty_chunk_issues(
                prompt_context.chunks,
            )
        )

        issues.extend(
            self._duplicate_chunk_issues(
                prompt_context.chunks,
            )
        )

        issues.extend(
            self._citation_consistency_issues(
                prompt_context,
            )
        )

        return ValidatorOutcome(
            issues=issues,
        )

    def _empty_chunk_issues(
        self,
        chunks: list[ContextChunk],
    ) -> list[ValidationIssue]:

        empty_chunk_ids = [chunk.chunk_id for chunk in chunks if not chunk.content.strip()]

        if not empty_chunk_ids:
            return []

        return [
            ValidationIssue(
                validator=self.name,
                severity=ValidationSeverity.WARNING,
                message=(f"{len(empty_chunk_ids)} retrieved chunk(s) have empty content."),
                details={
                    "empty_chunk_ids": [str(chunk_id) for chunk_id in empty_chunk_ids],
                },
            )
        ]

    def _duplicate_chunk_issues(
        self,
        chunks: list[ContextChunk],
    ) -> list[ValidationIssue]:

        counts = Counter(chunk.chunk_id for chunk in chunks)

        duplicate_ids = [chunk_id for chunk_id, count in counts.items() if count > 1]

        if not duplicate_ids:
            return []

        return [
            ValidationIssue(
                validator=self.name,
                severity=ValidationSeverity.WARNING,
                message=(
                    f"{len(duplicate_ids)} chunk_id(s) appear more than once in prompt_context."
                ),
                details={
                    "duplicate_chunk_ids": [str(chunk_id) for chunk_id in duplicate_ids],
                },
            )
        ]

    def _citation_consistency_issues(
        self,
        prompt_context: PromptContext,
    ) -> list[ValidationIssue]:

        citation_ids = {citation.citation_id for citation in prompt_context.citations}

        chunk_citation_ids = {
            chunk.citation_id for chunk in prompt_context.chunks if chunk.citation_id
        }

        orphaned_chunk_citations = sorted(
            chunk_citation_ids - citation_ids,
        )

        if not orphaned_chunk_citations:
            return []

        return [
            ValidationIssue(
                validator=self.name,
                severity=ValidationSeverity.WARNING,
                message=(
                    "Chunk(s) reference citation_id(s) not present in "
                    f"prompt_context.citations: {', '.join(orphaned_chunk_citations)}."
                ),
                details={
                    "orphaned_citation_ids": orphaned_chunk_citations,
                },
            )
        ]
