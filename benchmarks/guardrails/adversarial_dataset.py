"""
Adversarial dataset schema (EVALUATION_PLAN.md §9, MVP slice).

Deliberately separate from `rag_answer_gold` (`benchmarks/generation/golden_dataset.py`)
per §3: security/guardrail testing needs deliberately malicious inputs,
and mixing them into the main dataset would contaminate the query-type
distributions used for other reporting. Reuses the guardrails platform's
own real enums (`GuardrailStage`/`GuardrailCategory`/`GuardrailSeverity`,
`app.ai.guardrails.enums`) rather than inventing parallel ones, so a case
can never reference a stage/category that doesn't actually exist in the
system being tested.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity, GuardrailStage
from pydantic import BaseModel, ConfigDict, Field


class PayloadLocation(StrEnum):
    USER_PROMPT = "user_prompt"
    SYSTEM_PROMPT = "system_prompt"
    RETRIEVED_CHUNK = "retrieved_chunk"
    CITATION_ATTACK = "citation_attack"
    """Not a text payload -- the attack is a structural mismatch between
    citations and retrieved chunks. See `attack_variant`."""


class AdversarialCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str

    technique: str = Field(
        description="Short human-readable name for the attack technique.",
    )

    stage: GuardrailStage

    category: GuardrailCategory

    payload: str = ""
    """The malicious text. Empty for `CITATION_ATTACK` cases, which have
    no free-text payload -- see `attack_variant`."""

    payload_location: PayloadLocation

    attack_variant: str | None = None
    """Free-form sub-type discriminator, only meaningful for
    `CITATION_ATTACK` cases: "unknown_chunk_reference" or
    "unresolved_citation" -- the two distinct structural attacks
    `CitationIntegrityGuardrail` checks for."""

    expected_detected: bool
    """
    Whether the real guardrail is expected to flag this case. **Not all
    `True`** -- per EVALUATION_PLAN.md §9's own acceptance bar, a set
    where every case is detected isn't adversarial enough. Several cases
    here are deliberately evasive (paraphrase, unicode homoglyphs) and
    `expected_detected=False`, documenting a real, known gap rather than
    hiding it.
    """

    expected_category: GuardrailCategory | None = None
    """Category the guardrail is expected to assign when detected --
    None when `expected_detected` is False (nothing to check)."""

    expected_severity: GuardrailSeverity | None = None
    """Severity the guardrail is expected to assign when detected --
    None when `expected_detected` is False."""

    notes: str = ""


class AdversarialDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str

    notes: str = ""

    cases: list[AdversarialCase]


def load_adversarial_dataset(path: Path) -> AdversarialDataset:
    """
    Raises:
        FileNotFoundError: If the dataset file does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(f"Adversarial dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return AdversarialDataset.model_validate(payload)
