"""
Ingestion fidelity metrics (EVALUATION_PLAN.md §4).

Distinct from `benchmarks/chunking/`, which compares chunking strategies
against each other, this checks parse *fidelity* -- did Docling preserve
a document's actual structure -- against a handful of hand-verified,
labeled fixture documents. `benchmarks/chunking/` never checks this; it
only ever compares strategies to each other, not to a known-correct
source.

All functions are pure and framework-independent so they can be unit
tested without a running processing pipeline.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)

# A Markdown pipe table: a header row, a separator row (---/:--/etc.),
# then one or more data rows.
_TABLE_RE = re.compile(r"^\|.+\|\n\|[-: |]+\|\n(?:\|.+\|\n?)+", re.MULTILINE)


class MarkdownStructure(BaseModel):
    """Structure extracted from a document's Markdown export."""

    model_config = ConfigDict(extra="forbid")

    heading_count: int
    table_count: int


def extract_markdown_structure(
    markdown: str,
) -> MarkdownStructure:
    """
    Extract heading and table counts from a document's Markdown export.

    Deliberately structural, not semantic -- this catches "Docling
    stopped emitting `#` headings" or "table rows collapsed into plain
    text," not "the heading text is slightly different," which would be
    a much noisier, harder-to-maintain check for the same fidelity
    signal.
    """

    headings = _HEADING_RE.findall(markdown)
    tables = _TABLE_RE.findall(markdown)

    return MarkdownStructure(
        heading_count=len(headings),
        table_count=len(tables),
    )


def parse_success_rate(
    outcomes: list[bool],
) -> float:
    """
    Fraction of ingestion attempts that succeeded.

    `outcomes` is a list of per-document success booleans -- in
    production, `DocumentProcessingStatus.COMPLETED` vs `.FAILED`
    (`app/models/enums.py`); in this benchmark, whether a fixture's
    cached `processed_document.json` loaded and validated at all.
    """

    if not outcomes:
        return 0.0

    return sum(1 for outcome in outcomes if outcome) / len(outcomes)


def preservation_score(
    *,
    actual_count: int,
    expected_min_count: int,
) -> float:
    """
    How much of a fixture's known-correct structure survived parsing,
    as a 0-1 ratio.

    1.0 once `actual_count` meets or exceeds the hand-verified minimum
    (parsing sometimes finds *more* structure than the minimum recorded
    at fixture-curation time, e.g. a Docling version upgrade -- that's
    not a regression). A minimum of 0 (a fixture with no expected
    headings/tables of that kind) trivially scores 1.0.
    """

    if expected_min_count <= 0:
        return 1.0

    return min(actual_count / expected_min_count, 1.0)
