"""
Context-construction evaluation (EVALUATION_PLAN.md §6, §18 Level 1).

New layer, so -- same as citation validity (E4) and ingestion fidelity
(E12) -- no existing stub file name fits; this gets its own file.

Covers `app/ai/knowledge/context/quality.py`:
- Provenance preservation is true when every citation's claimed chunks
  are present in the final `PromptContext.chunks`
- Provenance preservation catches a chunk silently dropped after a
  citation was built for it (the exact "fusion/rerank/compression
  dropped evidence" failure mode §6 exists to catch)
- Token efficiency is a bounded-below-by-zero ratio, computed
  deterministically without any live token-counting API call
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.knowledge.context.quality import check_context_construction

from tests.unit.ai.runtime.generation.validation.factories import (
    make_chunk,
    make_citation,
    make_prompt_context,
)


def test_provenance_preserved_when_every_citation_chunk_survived() -> None:
    chunk_id = uuid4()

    context = make_prompt_context(
        context="Formatted context including the retrieved passage.",
        chunks=[make_chunk(citation_id="S1", chunk_id=chunk_id, content="The sky is blue.")],
        citations=[make_citation(citation_id="S1", chunk_ids=[chunk_id])],
    )

    report = check_context_construction(prompt_context=context)

    assert report.provenance_preserved
    assert report.unprovenanced_citation_ids == []


def test_provenance_not_preserved_when_a_cited_chunk_was_dropped() -> None:
    """
    The exact failure mode this layer exists to catch: retrieval found
    the right chunk, a Citation was built referencing it, but a later
    compression/fusion step dropped the chunk from the final context --
    the response can still look fine, since generation never sees the
    gap directly.
    """

    dropped_chunk_id = uuid4()

    context = make_prompt_context(
        chunks=[],  # the chunk never made it into the final context
        citations=[make_citation(citation_id="S1", chunk_ids=[dropped_chunk_id])],
    )

    report = check_context_construction(prompt_context=context)

    assert not report.provenance_preserved
    assert report.unprovenanced_citation_ids == ["S1"]


def test_provenance_preserved_trivially_when_there_are_no_citations() -> None:
    context = make_prompt_context(chunks=[], citations=[])

    report = check_context_construction(prompt_context=context)

    assert report.provenance_preserved
    assert report.unprovenanced_citation_ids == []


def test_token_efficiency_is_the_ratio_of_evidence_to_total_context() -> None:
    context = make_prompt_context(
        context="word " * 100,  # 100-word formatted context
        chunks=[make_chunk(content="word " * 50)],  # 50-word evidence chunk
    )

    report = check_context_construction(prompt_context=context)

    assert report.context_token_count > 0
    assert report.evidence_token_count > 0
    # Evidence is roughly half the formatted context by word count, so
    # token efficiency should land near 0.5 regardless of the exact
    # words-to-tokens constant used.
    assert 0.3 < report.token_efficiency < 0.7


def test_token_efficiency_is_zero_when_context_is_empty() -> None:
    context = make_prompt_context(context="", chunks=[])

    report = check_context_construction(prompt_context=context)

    assert report.context_token_count == 0
    assert report.token_efficiency == 0.0


def test_token_efficiency_sums_across_multiple_chunks() -> None:
    context = make_prompt_context(
        context="word " * 100,
        chunks=[
            make_chunk(citation_id="S1", content="word " * 20),
            make_chunk(citation_id="S2", content="word " * 30),
        ],
    )

    report = check_context_construction(prompt_context=context)

    single_chunk_context = make_prompt_context(
        context="word " * 100,
        chunks=[make_chunk(citation_id="S1", content="word " * 20)],
    )
    single_chunk_report = check_context_construction(prompt_context=single_chunk_context)

    assert report.evidence_token_count > single_chunk_report.evidence_token_count
