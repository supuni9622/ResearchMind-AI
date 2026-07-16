from __future__ import annotations

import re

from app.ai.guardrails.utils.patterns import PII_PATTERNS, match_any


def test_match_any_returns_matching_pattern_names() -> None:
    patterns = {
        "foo": re.compile(r"foo"),
        "bar": re.compile(r"bar"),
    }

    assert match_any("this has foo in it", patterns) == ["foo"]


def test_match_any_returns_empty_list_when_nothing_matches() -> None:
    patterns = {"foo": re.compile(r"foo")}

    assert match_any("nothing here", patterns) == []


def test_pii_patterns_detect_email() -> None:
    assert match_any("contact me at a@example.com", PII_PATTERNS) == ["email"]


def test_pii_patterns_detect_credit_card_shaped_number() -> None:
    assert "credit_card" in match_any("4111 1111 1111 1111", PII_PATTERNS)


def test_pii_patterns_detect_api_key_shaped_token() -> None:
    assert "api_key" in match_any("sk-abcdefghijklmnopqrstuvwx", PII_PATTERNS)
