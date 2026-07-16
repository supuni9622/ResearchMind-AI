from __future__ import annotations

from enum import StrEnum


class GuardrailSeverity(StrEnum):
    INFO = "info"

    WARNING = "warning"

    ERROR = "error"

    CRITICAL = "critical"


class GuardrailStage(StrEnum):
    INPUT = "input"

    RETRIEVAL = "retrieval"

    GENERATION = "generation"

    RUNTIME = "runtime"


class GuardrailCategory(StrEnum):
    PROMPT_INJECTION = "prompt_injection"

    JAILBREAK = "jailbreak"

    PII = "pii"

    SOURCE_TRUST = "source_trust"

    FAITHFULNESS = "faithfulness"

    BUDGET = "budget"

    LOOP = "loop"

    TOOL_POLICY = "tool_policy"

    ACCESS_CONTROL = "access_control"

    SCOPE = "scope"
    """Off-topic / out-of-scope input (PRD §8 Scope Validation) — not in the
    PRD §7 enum literal, but §8 names the check, so a category is added."""

    SCHEMA = "schema"
    """Structured-output schema violations (PRD §10 Schema Enforcement)."""

    CITATION_INTEGRITY = "citation_integrity"
    """Citation/chunk/document existence checks (PRD §9 Citation Integrity)."""

    MODERATION = "moderation"
    """Foundation-only content moderation (PRD §10 Moderation)."""

    SYSTEM = "system"
    """A guardrail check itself failed to run (see `GuardrailService._run_check`)
    — not a policy trigger, an internal error surfaced as an issue."""


class GuardrailAction(StrEnum):
    ALLOW = "allow"

    WARN = "warn"

    BLOCK = "block"

    REGENERATE = "regenerate"

    ESCALATE = "escalate"
