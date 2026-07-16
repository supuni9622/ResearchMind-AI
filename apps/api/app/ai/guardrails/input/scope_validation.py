from __future__ import annotations

import re

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.runtime.generation.models import GenerationRequest

#
# PRD §8: ResearchMind should stay "research-focused" -- flags requests
# that look like creative writing or hacking assistance rather than
# research. Deliberately small and low-recall: a research platform's
# false-positive cost (blocking a legitimate query) is much higher than
# its false-negative cost (missing an off-topic one), and PRD §23 caps
# false positives at <5%. This never escalates past WARNING.
#

_OFF_SCOPE_TRIGGERS: dict[str, list[re.Pattern[str]]] = {
    "creative_writing": [
        re.compile(r"write\s+(me\s+)?a\s+(romantic\s+)?poem", re.IGNORECASE),
        re.compile(r"write\s+(me\s+)?a\s+love\s+letter", re.IGNORECASE),
        re.compile(r"write\s+(me\s+)?a\s+(short\s+)?story", re.IGNORECASE),
    ],
    "hacking": [
        re.compile(r"how\s+to\s+hack", re.IGNORECASE),
        re.compile(r"bypass\s+(security|authentication|login)", re.IGNORECASE),
        re.compile(r"crack\s+(a\s+)?password", re.IGNORECASE),
    ],
}


class ScopeValidationGuardrail(
    InputGuardrailInterface,
):
    """
    Deterministic off-topic heuristic keeping ResearchMind research-
    focused (PRD §8). Foundation-depth: a small keyword-category
    denylist, not a classifier.
    """

    @property
    def name(
        self,
    ) -> str:
        return "scope_validation"

    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:

        text = request.user_prompt

        issues: list[GuardrailIssue] = []

        for category, patterns in _OFF_SCOPE_TRIGGERS.items():
            if any(pattern.search(text) for pattern in patterns):
                issues.append(
                    GuardrailIssue(
                        code="off_scope_request",
                        severity=GuardrailSeverity.WARNING,
                        category=GuardrailCategory.SCOPE,
                        message=f"Input looks like an off-scope '{category}' request.",
                        metadata={"off_scope_category": category},
                    )
                )

        return issues
