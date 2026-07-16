from __future__ import annotations

import re

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.interfaces import InputGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.utils.patterns import match_any
from app.ai.runtime.generation.models import GenerationRequest

#
# PRD §8 examples: "ignore previous instructions", "reveal system prompt",
# "show developer instructions", "simulate admin", "act as DAN". This is a
# distinct table from `knowledge/context/guardrails/providers/rule_based.py`'s
# `PATTERNS` -- that one targets *retrieved chunk content* and includes
# retrieval-specific triggers (tool_call/browse/send_email) that don't
# apply to a direct user prompt. Both go through the same `match_any()`
# helper, just with different pattern tables.
#

_INJECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "ignore_previous_instructions": re.compile(
        r"ignore\s+.*instructions",
        re.IGNORECASE,
    ),
    "reveal_system_prompt": re.compile(
        r"(reveal|show|print)\s+.*(system\s+prompt|hidden\s+prompt)",
        re.IGNORECASE,
    ),
    "developer_instructions": re.compile(
        r"(developer|assistant)\s+instructions",
        re.IGNORECASE,
    ),
    "simulate_admin": re.compile(
        r"(simulate|pretend\s+to\s+be|act\s+as)\s+(an?\s+)?admin",
        re.IGNORECASE,
    ),
    "act_as_dan": re.compile(
        r"\bDAN\b|do\s+anything\s+now",
        re.IGNORECASE,
    ),
    "jailbreak": re.compile(
        r"jailbreak",
        re.IGNORECASE,
    ),
}

_JAILBREAK_TRIGGERS = {"act_as_dan", "jailbreak"}


class PromptInjectionGuardrail(
    InputGuardrailInterface,
):
    """
    Regex-based prompt injection / jailbreak detection on the user's
    direct input (PRD §8, P0). Deterministic by design (Principle 3) —
    a single trigger warns, but two or more triggers (or any
    jailbreak-specific trigger) escalates to an error, mirroring the
    suspicious/malicious split already used by
    `knowledge/context/guardrails/providers/rule_based.py` for retrieved
    chunks.
    """

    @property
    def name(
        self,
    ) -> str:
        return "prompt_injection"

    async def check(
        self,
        request: GenerationRequest,
    ) -> list[GuardrailIssue]:

        text = f"{request.user_prompt}\n{request.system_prompt or ''}"

        triggered = match_any(
            text,
            _INJECTION_PATTERNS,
        )

        if not triggered:
            return []

        is_jailbreak = len(triggered) >= 2 or any(t in _JAILBREAK_TRIGGERS for t in triggered)

        if is_jailbreak:
            return [
                GuardrailIssue(
                    code="jailbreak_detected",
                    severity=GuardrailSeverity.ERROR,
                    category=GuardrailCategory.JAILBREAK,
                    message=f"Input matched multiple/jailbreak-specific triggers: {triggered}",
                    metadata={"triggers": triggered},
                )
            ]

        return [
            GuardrailIssue(
                code="prompt_injection_suspected",
                severity=GuardrailSeverity.WARNING,
                category=GuardrailCategory.PROMPT_INJECTION,
                message=f"Input matched a prompt-injection trigger: {triggered[0]}",
                metadata={"triggers": triggered},
            )
        ]
