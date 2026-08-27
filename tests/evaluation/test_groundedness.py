"""
Deterministic, no-LLM generation metrics (EVALUATION_PLAN.md §7's
CI-smoke tier, §18 Level 1) -- `benchmarks/generation/metrics.py`'s
lexical-overlap proxies (`groundedness`, `faithfulness`, `relevance`,
`completeness`, `citation_accuracy`), previously with zero direct test
coverage. Distinct from `test_faithfulness.py`, which covers the fuller,
LLM-judge Ragas tier (`ragas_scoring.py`) -- these two files are the
CI-smoke vs release-candidate tiers §13 describes, not an arbitrary split.
"""

from __future__ import annotations

from benchmarks.generation.metrics import (
    citation_accuracy,
    completeness,
    faithfulness,
    groundedness,
    relevance,
)

_CONTEXT = "Loop engineering treats the observe plan act evaluate cycle as a governance problem."


def test_groundedness_is_one_when_every_answer_word_appears_in_context() -> None:
    answer = "Loop engineering treats the cycle as a governance problem."

    assert groundedness(answer, _CONTEXT) == 1.0


def test_groundedness_drops_when_the_answer_introduces_unsupported_words() -> None:
    grounded = groundedness("Loop engineering treats the cycle as governance.", _CONTEXT)
    fabricated = groundedness(
        "Loop engineering secretly controls global financial markets.", _CONTEXT
    )

    assert fabricated < grounded


def test_groundedness_with_empty_answer_is_zero() -> None:
    assert groundedness("", _CONTEXT) == 0.0


def test_faithfulness_is_one_when_every_sentence_is_supported() -> None:
    answer = "Loop engineering treats the cycle as a governance problem."

    assert faithfulness(answer, _CONTEXT) == 1.0


def test_faithfulness_penalizes_an_unsupported_sentence_padded_onto_a_supported_one() -> None:
    supported_only = faithfulness("Loop engineering treats the cycle as governance.", _CONTEXT)
    padded = faithfulness(
        "Loop engineering treats the cycle as governance. "
        "The framework was invented in ancient Rome by philosophers.",
        _CONTEXT,
    )

    assert padded < supported_only


def test_faithfulness_with_no_sentences_is_zero() -> None:
    assert faithfulness("", _CONTEXT) == 0.0


def test_faithfulness_with_empty_context_is_zero() -> None:
    assert faithfulness("Loop engineering treats the cycle as governance.", "") == 0.0


def test_relevance_measures_query_word_coverage_in_the_answer() -> None:
    query = "What does loop engineering treat the cycle as?"
    on_topic = relevance("Loop engineering treats the cycle as a governance problem.", query)
    off_topic = relevance("The weather today is sunny with a light breeze.", query)

    assert on_topic > off_topic


def test_relevance_with_empty_query_is_zero() -> None:
    assert relevance("Some answer.", "") == 0.0


def test_completeness_measures_expected_answer_word_coverage() -> None:
    expected = "goal representation, state model, action executor, observation collector"
    complete = completeness(
        "The components are goal representation, state model, action executor, "
        "and observation collector.",
        expected,
    )
    incomplete = completeness("The components are goal representation only.", expected)

    assert complete > incomplete


def test_completeness_with_empty_expected_answer_is_zero() -> None:
    assert completeness("Some answer.", "") == 0.0


def test_citation_accuracy_is_one_when_nothing_was_expected() -> None:
    assert citation_accuracy("Some answer.", cited_filenames=[], expected_filenames=[]) == 1.0


def test_citation_accuracy_counts_structured_citations() -> None:
    score = citation_accuracy(
        "Some answer.",
        cited_filenames=["paper-a.pdf"],
        expected_filenames=["paper-a.pdf", "paper-b.pdf"],
    )

    assert score == 0.5


def test_citation_accuracy_counts_filenames_mentioned_in_answer_text() -> None:
    score = citation_accuracy(
        "According to paper-a.pdf, the finding holds.",
        cited_filenames=[],
        expected_filenames=["paper-a.pdf"],
    )

    assert score == 1.0


def test_citation_accuracy_is_zero_when_expected_citations_are_entirely_missing() -> None:
    score = citation_accuracy(
        "Some answer with no citations at all.",
        cited_filenames=[],
        expected_filenames=["paper-a.pdf"],
    )

    assert score == 0.0
