"""
Importance scoring (PRD §16) -- keeps `MemoryService.remember()` from
persisting every low-signal utterance ("hello", "thanks", "yes").

Deliberately a rule-based heuristic rather than an LLM call: it runs on
every `remember()`, must be cheap, and the PRD's own examples (§16) are
simple enough for pattern matching. `ExtractedMemory.importance` (PRD
§17, LLM-driven extraction) is the future path for higher-fidelity
scoring -- this module is not that pipeline.
"""

from __future__ import annotations

import re

from app.ai.guardrails.utils.patterns import match_any

LOW_SIGNAL_PHRASES: frozenset[str] = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "thx",
        "yes",
        "no",
        "ok",
        "okay",
        "sure",
        "bye",
        "goodbye",
        "cool",
        "great",
        "nice",
        "got it",
        "sounds good",
    }
)

HIGH_SIGNAL_PATTERNS: dict[str, re.Pattern[str]] = {
    "preference": re.compile(
        r"\b(prefer|favorite|favourite|always use|never use|I like|I don't like|I hate)\b",
        re.IGNORECASE,
    ),
    "instruction": re.compile(
        r"\b(remember that|please remember|don't forget|keep in mind|from now on)\b",
        re.IGNORECASE,
    ),
    "research_interest": re.compile(
        r"\b(research(ing)?|studying|working on|interested in|focus(ed)? on)\b",
        re.IGNORECASE,
    ),
    "finding": re.compile(
        r"\b(finding|conclusion|result|evidence|citation|hypothesis)\b",
        re.IGNORECASE,
    ),
}

_LENGTH_FLOOR = 0.1
_LENGTH_CEILING = 0.5
_LENGTH_NORMALIZER = 400.0

_PER_SIGNAL_BOOST = 0.15

_LOW_SIGNAL_SCORE = 0.05

_MIN_MEANINGFUL_LENGTH = 4


def score_importance(content: str) -> float:
    """
    Score `content` in `[0, 1]` -- higher means more worth persisting.

    Trivial acknowledgements score near zero; longer content and
    content matching a preference/instruction/research/finding signal
    scores progressively higher.
    """

    normalized = content.strip().lower().rstrip(".!?")

    if not normalized or len(normalized) < _MIN_MEANINGFUL_LENGTH:
        return _LOW_SIGNAL_SCORE

    if normalized in LOW_SIGNAL_PHRASES:
        return _LOW_SIGNAL_SCORE

    length_score = min(
        _LENGTH_CEILING,
        _LENGTH_FLOOR + (len(content) / _LENGTH_NORMALIZER),
    )

    matched_signals = match_any(content, HIGH_SIGNAL_PATTERNS)

    score = length_score + (_PER_SIGNAL_BOOST * len(matched_signals))

    return round(min(1.0, max(0.0, score)), 2)
