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

_DEFAULT_MIN_CHARS = 1

_DEFAULT_MAX_CHARS = 200_000

#
# Provider-reported finish reasons that mean "the provider stopped
# because it hit a token/length ceiling, not because it was done" --
# OpenAI/Groq report "length", Claude reports "max_tokens". Gemini and
# Ollama don't populate finish_reason at all yet (see providers/*.py),
# so this check is a no-op for those two until they do.
#

_TRUNCATION_FINISH_REASONS = frozenset(
    {
        "length",
        "max_tokens",
    },
)


class ResponseSizeValidator(
    OutputValidatorInterface,
):
    """
    Checks `GenerationResult.content` falls within a configured size
    range, and flags a likely-truncated response (the provider stopped
    for hitting a token ceiling rather than reaching a natural end).

    Bounds are configurable per instance rather than hard-coded so a
    runtime with different expectations (e.g. a one-word classification
    response vs. a multi-page report) can compose its own instance
    instead of sharing the default pipeline's thresholds.
    """

    def __init__(
        self,
        *,
        min_chars: int = _DEFAULT_MIN_CHARS,
        max_chars: int = _DEFAULT_MAX_CHARS,
    ) -> None:
        self._min_chars = min_chars

        self._max_chars = max_chars

    @property
    def name(
        self,
    ) -> str:
        return "response_size"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        length = len(
            result.content,
        )

        issues: list[ValidationIssue] = []

        if length < self._min_chars:
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Response content is {length} char(s), below the "
                        f"minimum of {self._min_chars}."
                    ),
                    details={
                        "length": length,
                        "min_chars": self._min_chars,
                    },
                )
            )

        if length > self._max_chars:
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Response content is {length} char(s), above the "
                        f"maximum of {self._max_chars}."
                    ),
                    details={
                        "length": length,
                        "max_chars": self._max_chars,
                    },
                )
            )

        if result.finish_reason in _TRUNCATION_FINISH_REASONS:
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.WARNING,
                    message=(
                        f"Response finished with reason '{result.finish_reason}', "
                        "indicating it may have been truncated by a token limit."
                    ),
                    details={
                        "finish_reason": result.finish_reason,
                    },
                )
            )

        return ValidatorOutcome(
            issues=issues,
        )
