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
    ValidatorOutcome,
)

#
# Deterministic, no-LLM groundedness proxy (PRD §10): what fraction of
# the response's "significant" words (length >= 4, alphanumeric) also
# appear somewhere in the retrieved context. This is a lexical-overlap
# heuristic, not semantic similarity — cheap and fast (Principle 2 —
# avoid expensive/LLM calls), but coarser than the PRD's proposed
# `source_overlap_validator` (semantic similarity). Deliberately biased
# toward under-flagging (WARNING only, threshold kept low) per the
# PRD's <5% false-hallucination-detection success metric — this is a
# rough signal to surface, not a gate to fail generations on.
#

_WORD_RE = re.compile(
    r"[A-Za-z0-9]{4,}",
)

_MIN_SIGNIFICANT_WORDS = 5
"""Below this many significant words, the score is too noisy to be meaningful."""

_LOW_GROUNDEDNESS_THRESHOLD = 0.3


class HallucinationValidator(
    OutputValidatorInterface,
):
    """
    Lightweight groundedness check: flags responses whose content has
    little lexical overlap with the retrieved context, as a proxy for
    unsupported/fabricated claims. Runs only when there's retrieved
    context to ground against.
    """

    @property
    def name(
        self,
    ) -> str:
        return "hallucination"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        prompt_context = result.request.prompt_context

        context_words = self._significant_words(
            prompt_context.context,
        )

        if not context_words:
            return ValidatorOutcome()

        response_words = self._significant_words(
            result.content,
        )

        if len(response_words) < _MIN_SIGNIFICANT_WORDS:
            return ValidatorOutcome()

        overlapping = response_words & context_words

        groundedness_score = len(overlapping) / len(response_words)

        if groundedness_score >= _LOW_GROUNDEDNESS_THRESHOLD:
            return ValidatorOutcome(
                score=groundedness_score,
            )

        return ValidatorOutcome(
            issues=[
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        "Response has low lexical overlap with the retrieved context "
                        f"(groundedness score {groundedness_score:.2f}); it may "
                        "contain unsupported or fabricated claims."
                    ),
                    details={
                        "groundedness_score": groundedness_score,
                    },
                )
            ],
            score=groundedness_score,
        )

    @staticmethod
    def _significant_words(
        text: str,
    ) -> set[str]:
        return {word.lower() for word in _WORD_RE.findall(text)}
