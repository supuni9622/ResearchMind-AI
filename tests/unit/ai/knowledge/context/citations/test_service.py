"""
Unit tests for the canonical CitationService
(app.ai.knowledge.context.citations.service).

Covers:
- Each chunk produces one Citation, numbered "S1", "S2", ... in order
- The generated citation_id is also written back onto the source chunk
- Citation fields are mapped from the chunk (filename, document_id,
  page_numbers, heading, heading_path)
- chunk_ids falls back to [chunk.chunk_id] when the chunk wasn't
  produced by an adjacent-merge (merged_chunk_ids empty), and uses
  merged_chunk_ids when it was
- Empty input returns an empty CitationResult
"""

from __future__ import annotations

from app.ai.knowledge.context.citations.service import CitationService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


async def test_build_numbers_citations_starting_at_one() -> None:
    first = make_context_chunk()
    second = make_context_chunk()

    result = await CitationService().build([first, second])

    assert [citation.citation_id for citation in result.citations] == ["S1", "S2"]


async def test_build_writes_the_citation_id_back_onto_the_chunk() -> None:
    chunk = make_context_chunk()

    await CitationService().build([chunk])

    assert chunk.citation_id == "S1"


async def test_build_maps_citation_fields_from_the_chunk() -> None:
    chunk = make_context_chunk(filename="paper.pdf")
    chunk.page_numbers = [3, 4]
    chunk.heading = "Results"
    chunk.heading_path = ["Body", "Results"]

    result = await CitationService().build([chunk])

    citation = result.citations[0]
    assert citation.filename == "paper.pdf"
    assert citation.document_id == chunk.document_id
    assert citation.page_numbers == [3, 4]
    assert citation.heading == "Results"
    assert citation.heading_path == ["Body", "Results"]


async def test_build_uses_chunk_id_when_not_merged() -> None:
    chunk = make_context_chunk()

    result = await CitationService().build([chunk])

    assert result.citations[0].chunk_ids == [chunk.chunk_id]


async def test_build_uses_merged_chunk_ids_when_present() -> None:
    chunk = make_context_chunk()
    chunk.merged_chunk_ids = [chunk.chunk_id, chunk.chunk_id]

    result = await CitationService().build([chunk])

    assert result.citations[0].chunk_ids == chunk.merged_chunk_ids


async def test_build_empty_chunks_returns_empty_result() -> None:
    result = await CitationService().build([])

    assert result.citations == []
