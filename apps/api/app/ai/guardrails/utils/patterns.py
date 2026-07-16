from __future__ import annotations

import re


def match_any(
    text: str,
    patterns: dict[str, re.Pattern[str]],
) -> list[str]:
    """Returns the names of every pattern that matches `text`."""

    return [name for name, pattern in patterns.items() if pattern.search(text)]


PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(
        r"[\w.+-]+@[\w-]+\.[\w.-]+",
    ),
    "credit_card": re.compile(
        r"\b(?:\d[ -]*?){13,19}\b",
    ),
    "api_key": re.compile(
        r"\b(sk|pk|AKIA)[A-Za-z0-9_-]{16,}\b",
    ),
    "generic_token": re.compile(
        r"\b[A-Za-z0-9_-]{32,}\b",
    ),
}
"""
Shared across `input/pii_detection.py` and `generation/pii_leakage.py` —
the one genuine multi-consumer regex table in this platform (PRD §8/§10
both call for the same email/credit-card/API-key/token detection,
foundation-only depth).
"""
