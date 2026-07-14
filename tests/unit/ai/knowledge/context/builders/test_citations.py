"""
Unit tests for CitationService.

Covers:
- Each chunk produces a numbered "[Source N]" section (1-based)
- Section includes the chunk's filename, chunk_index, and content
- Sections are joined in input order
- Empty input produces an empty string
"""

from __future__ import annotations

from app.ai.knowledge.context.builders.citations import CitationService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def test_build_numbers_sources_starting_at_one() -> None:
    first = make_context_chunk(filename="a.pdf", chunk_index=0, content="alpha")
    second = make_context_chunk(filename="b.pdf", chunk_index=1, content="beta")

    result = CitationService().build([first, second])

    first_pos = result.index("[Source 1]")
    second_pos = result.index("[Source 2]")
    assert first_pos < second_pos
    assert "a.pdf" in result
    assert "alpha" in result
    assert "b.pdf" in result
    assert "beta" in result


def test_build_includes_chunk_filename_index_and_content() -> None:
    chunk = make_context_chunk(filename="research.pdf", chunk_index=3, content="the content")

    result = CitationService().build([chunk])

    assert "[Source 1]" in result
    assert "research.pdf" in result
    assert "3" in result
    assert "the content" in result


def test_build_empty_chunks_returns_empty_string() -> None:
    assert CitationService().build([]) == ""
