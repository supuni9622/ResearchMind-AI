"""
Unit tests for ingestion fidelity metrics.

Covers:
- `extract_markdown_structure` counts ATX headings (# through ######)
  and Markdown pipe tables, ignoring plain text/prose
- `parse_success_rate` handles the empty-attempts case without raising
- `preservation_score` reaches 1.0 once the actual count meets the
  hand-verified minimum, degrades proportionally below it, and treats a
  zero minimum as trivially satisfied
"""

from __future__ import annotations

from benchmarks.ingestion.metrics import (
    extract_markdown_structure,
    parse_success_rate,
    preservation_score,
)

_SAMPLE_TABLE = "| A | B |\n|---|---|\n| 1 | 2 |\n"


def test_extract_markdown_structure_counts_headings() -> None:
    markdown = "# Title\n\nSome text.\n\n## Section\n\nMore text.\n\n### Subsection\n"

    structure = extract_markdown_structure(markdown)

    assert structure.heading_count == 3
    assert structure.table_count == 0


def test_extract_markdown_structure_counts_pipe_tables() -> None:
    markdown = f"# Title\n\n{_SAMPLE_TABLE}\nSome trailing prose.\n"

    structure = extract_markdown_structure(markdown)

    assert structure.table_count == 1


def test_extract_markdown_structure_counts_multiple_tables() -> None:
    markdown = f"{_SAMPLE_TABLE}\nBetween tables.\n\n{_SAMPLE_TABLE}"

    structure = extract_markdown_structure(markdown)

    assert structure.table_count == 2


def test_extract_markdown_structure_ignores_plain_text() -> None:
    markdown = "Just a paragraph with no headings or tables at all."

    structure = extract_markdown_structure(markdown)

    assert structure.heading_count == 0
    assert structure.table_count == 0


def test_extract_markdown_structure_does_not_confuse_a_hash_in_prose_with_a_heading() -> None:
    markdown = "The price is #10 on the list, not a heading.\n"

    structure = extract_markdown_structure(markdown)

    assert structure.heading_count == 0


def test_parse_success_rate_with_all_successes() -> None:
    assert parse_success_rate([True, True, True]) == 1.0


def test_parse_success_rate_with_a_mix() -> None:
    assert parse_success_rate([True, True, False, False]) == 0.5


def test_parse_success_rate_with_no_attempts_is_zero() -> None:
    assert parse_success_rate([]) == 0.0


def test_preservation_score_is_one_when_actual_meets_the_minimum() -> None:
    assert preservation_score(actual_count=17, expected_min_count=17) == 1.0


def test_preservation_score_is_one_when_actual_exceeds_the_minimum() -> None:
    # A newer Docling version finding *more* structure than the fixture
    # was curated with is not a regression.
    assert preservation_score(actual_count=25, expected_min_count=17) == 1.0


def test_preservation_score_degrades_proportionally_below_the_minimum() -> None:
    assert preservation_score(actual_count=5, expected_min_count=10) == 0.5


def test_preservation_score_with_zero_actual_and_nonzero_minimum_is_zero() -> None:
    assert preservation_score(actual_count=0, expected_min_count=10) == 0.0


def test_preservation_score_with_zero_minimum_is_trivially_satisfied() -> None:
    assert preservation_score(actual_count=0, expected_min_count=0) == 1.0
