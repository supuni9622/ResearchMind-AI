from __future__ import annotations

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

_WARN_UTILIZATION = 0.9
"""Warn once the estimated prompt is this fraction of the context window."""


class TokenBudgetValidator(
    InputValidatorInterface,
):
    """
    Checks the estimated prompt size against the resolved provider's
    context window.

    Deliberately does *not* use `observability/token_counter.py`'s
    `TokenCounter` — it makes real provider API calls (Claude/Gemini
    token-counting endpoints) to get an exact count, which is the
    right tradeoff for cost/latency observability but the wrong one
    here: Validation Platform Principle 2 (PRD §4) is to stay
    deterministic and avoid expensive calls. This uses the same
    words * 1.3 approximation `TokenCounter` itself falls back to on
    error, so it's already the system's agreed "good enough" estimate.

    Only runs when `context.context_window` is supplied — with no
    window to compare against there's nothing to check.
    """

    @property
    def name(
        self,
    ) -> str:
        return "token_budget"

    async def validate(
        self,
        request: GenerationRequest,
        context: InputValidationContext,
    ) -> ValidatorOutcome:

        if context.context_window is None or context.context_window <= 0:
            return ValidatorOutcome()

        prompt_text = request.user_prompt + (request.system_prompt or "")

        estimated_prompt_tokens = self._estimate_tokens(
            prompt_text,
        )

        requested_completion_tokens = request.max_tokens or 0

        total_estimated = estimated_prompt_tokens + requested_completion_tokens

        utilization = total_estimated / context.context_window

        score = max(
            0.0,
            min(
                1.0,
                1.0 - utilization,
            ),
        )

        if total_estimated > context.context_window:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Estimated tokens (~{total_estimated}, prompt "
                            f"~{estimated_prompt_tokens} + requested completion "
                            f"{requested_completion_tokens}) exceed the provider's "
                            f"context window ({context.context_window})."
                        ),
                        details={
                            "estimated_prompt_tokens": estimated_prompt_tokens,
                            "requested_completion_tokens": requested_completion_tokens,
                            "context_window": context.context_window,
                        },
                    )
                ],
                score=score,
            )

        if utilization >= _WARN_UTILIZATION:
            return ValidatorOutcome(
                issues=[
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.WARNING,
                        message=(
                            f"Estimated tokens (~{total_estimated}) are at "
                            f"{utilization:.0%} of the provider's context window "
                            f"({context.context_window}); little headroom remains."
                        ),
                        details={
                            "estimated_prompt_tokens": estimated_prompt_tokens,
                            "requested_completion_tokens": requested_completion_tokens,
                            "context_window": context.context_window,
                        },
                    )
                ],
                score=score,
            )

        return ValidatorOutcome(
            score=score,
        )

    @staticmethod
    def _estimate_tokens(
        text: str,
    ) -> int:
        """1 token ≈ 0.75 words — matches `TokenCounter._count_approximate`."""

        words = len(
            text.split(),
        )

        return max(
            1,
            int(
                words * 1.3,
            ),
        )
