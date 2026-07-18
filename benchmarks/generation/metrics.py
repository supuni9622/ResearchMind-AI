"""
Generation evaluation metrics.

Deterministic, no-LLM lexical-overlap scorers -- the same approach
already established in production by
`app/ai/runtime/generation/validation/output/hallucination_validator.py`
("Deterministic, no-LLM groundedness proxy... avoid expensive/LLM
calls"). Reusing that convention here keeps benchmark scoring cheap,
reproducible, and independent of any provider, rather than introducing
an LLM-judge dependency for what is meant to be a fast, offline,
repeatable engineering benchmark.

All functions are pure and framework-independent so they can be unit
tested without a running generation stack.
"""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"[A-Za-z0-9]{4,}")

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_SENTENCE_SUPPORT_THRESHOLD = 0.4
"""
Fraction of a sentence's significant words that must appear in the
context for that sentence to count as "supported" by the evidence.
"""


def _significant_words(text: str) -> set[str]:
    return {word.lower() for word in _WORD_RE.findall(text)}


def groundedness(answer: str, context: str) -> float:
    """
    Fraction of the answer's significant words that also appear
    somewhere in the retrieved context.

    Token-level containment: measures whether the answer's vocabulary
    as a whole originates from the evidence, without regard to how the
    words are assembled into claims.
    """

    answer_words = _significant_words(answer)

    if not answer_words:
        return 0.0

    context_words = _significant_words(context)

    return len(answer_words & context_words) / len(answer_words)


def faithfulness(answer: str, context: str) -> float:
    """
    Fraction of the answer's sentences whose claims are individually
    supported by the context.

    Sentence-level support: unlike `groundedness` (bag-of-words over the
    whole answer), this checks each claim independently, so an answer
    that pads a supported sentence with one fabricated sentence is
    penalized instead of averaged away.
    """

    sentences = [s for s in _SENTENCE_RE.split(answer.strip()) if s.strip()]

    if not sentences:
        return 0.0

    context_words = _significant_words(context)

    if not context_words:
        return 0.0

    supported = 0

    for sentence in sentences:
        sentence_words = _significant_words(sentence)

        if not sentence_words:
            continue

        overlap = len(sentence_words & context_words) / len(sentence_words)

        if overlap >= _SENTENCE_SUPPORT_THRESHOLD:
            supported += 1

    return supported / len(sentences)


def relevance(answer: str, query: str) -> float:
    """
    Fraction of the query's significant words addressed by the answer.

    Proxy for "did we answer the question" -- crude keyword coverage
    rather than semantic relevance, consistent with this benchmark
    suite's deterministic, no-LLM philosophy.
    """

    query_words = _significant_words(query)

    if not query_words:
        return 0.0

    answer_words = _significant_words(answer)

    return len(query_words & answer_words) / len(query_words)


def completeness(answer: str, expected_answer: str) -> float:
    """
    Fraction of the reference answer's significant words present in the
    generated answer.

    Proxy for "did we miss important information" -- coverage of the
    expected answer's key terms, not exact-match or semantic equivalence.
    """

    expected_words = _significant_words(expected_answer)

    if not expected_words:
        return 0.0

    answer_words = _significant_words(answer)

    return len(expected_words & answer_words) / len(expected_words)


def citation_accuracy(
    answer: str,
    cited_filenames: list[str],
    expected_filenames: list[str],
) -> float:
    """
    Fraction of the expected citation filenames actually referenced by
    the answer -- either via structured citations returned alongside the
    result, or mentioned directly in the answer text.

    Returns 1.0 when no citations were expected (nothing to miss).
    """

    if not expected_filenames:
        return 1.0

    answer_lower = answer.lower()

    referenced = {name.lower() for name in cited_filenames}
    referenced |= {name.lower() for name in expected_filenames if name.lower() in answer_lower}

    expected = {name.lower() for name in expected_filenames}

    return len(expected & referenced) / len(expected)
