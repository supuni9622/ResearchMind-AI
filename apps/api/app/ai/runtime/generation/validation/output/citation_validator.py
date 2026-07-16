from __future__ import annotations

import re

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
)

#
# Citation markers are bracketed identifiers, e.g. "[S1]" or "[S1, S2]" —
# see CitationService.build() (citation_id = "S{n}") and
# DefaultPromptFormatterProvider / AgentPromptFormatterProvider, which
# render sources into the prompt as "[{citation_id}] {filename}".
#

_BRACKET_RE = re.compile(
    r"\[([^\[\]]+)\]",
)

_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z][\w.-]*$",
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
    """

    @property
    def name(
        self,
    ) -> str:
        return "citation"

    async def validate(
        self,
        result: GenerationResult,
    ) -> list[ValidationIssue]:

        prompt_context = result.request.prompt_context

        known_ids = {citation.citation_id for citation in prompt_context.citations}

        known_ids |= {chunk.citation_id for chunk in prompt_context.chunks if chunk.citation_id}

        if not known_ids:
            return []

        referenced_ids = self._extract_citation_markers(
            result.content,
        )

        unknown_ids = sorted(
            referenced_ids - known_ids,
        )

        if not unknown_ids:
            return []

        return [
            ValidationIssue(
                validator=self.name,
                severity=ValidationSeverity.ERROR,
                message=(
                    "Response cites source(s) not present in the retrieved "
                    f"context: {', '.join(unknown_ids)}"
                ),
                details={
                    "unknown_citations": unknown_ids,
                    "known_citations": sorted(
                        known_ids,
                    ),
                },
            )
        ]

    @staticmethod
    def _extract_citation_markers(
        content: str,
    ) -> set[str]:

        referenced: set[str] = set()

        for match in _BRACKET_RE.finditer(
            content,
        ):
            for token in match.group(1).split(","):
                token = token.strip()

                if _IDENTIFIER_RE.match(
                    token,
                ):
                    referenced.add(
                        token,
                    )

        return referenced
