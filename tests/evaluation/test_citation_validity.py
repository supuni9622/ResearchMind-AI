"""
Cross-surface citation validator (EVALUATION_PLAN.md §8, §18 Level 1).

Named home for §8's citation checks per §18's stub-file mapping. None of
the six originally-named stub files
(`test_faithfulness.py`/`test_groundedness.py`/`test_reranking.py`/
`test_retrieval_precision.py`/`test_jailbreaks.py`/
`test_prompt_injection.py`) is actually a citation-specific name -- the
first three map cleanly to generation metrics (EVALUATION_IMPLEMENTATION_TRACKER.md
E1), `test_retrieval_precision.py` is retrieval's (E14, populated
separately), and the security pair is the adversarial dataset's (E15).
This file fills that naming gap explicitly rather than overloading an
unrelated stub.

Covers `app/ai/knowledge/context/citations/validity.py`:
- The strict core (`check_citation_validity`) treats an empty known-set
  as zero support, not a no-op -- distinct from the free-text wrapper
- The free-text wrapper (`check_prompt_context_citation_validity`)
  reintroduces the "nothing to check against" leniency
- Fabricated-citation-rate is computed correctly and bounded to [0, 1]
- Retrieval-provenance only evaluates when chunk-level data is supplied
- `CitationValidator` (the live, blocking validator) and `review_draft()`
  (Deep Research's synthesis-quality check) both still produce identical
  results after delegating to the shared core -- regression coverage for
  the refactor, complementing their own pre-existing unit tests.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.ai.knowledge.context.citations.service import CitationService
from app.ai.knowledge.context.citations.validity import (
    CitationCheckName,
    check_citation_validity,
    check_prompt_context_citation_validity,
    extract_citation_markers,
)
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.review import ReviewDecision, review_draft
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection

from benchmarks.generation.golden_dataset import (
    ExpectedBehavior,
    GoldenExample,
    load_golden_dataset,
)
from tests.unit.ai.runtime.generation.validation.factories import (
    make_chunk,
    make_citation,
    make_prompt_context,
)

GOLDEN_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "datasets" / "golden" / "rag_answer_gold.json"
)


def _draft(citation_ids: list[str]) -> ResearchDraft:
    return ResearchDraft(
        title="Title",
        abstract="Abstract",
        methodology="Method",
        discussion="Discussion",
        conclusion="Conclusion",
        findings=[ResearchDraftSection(heading="Finding", content="Text", citation_ids=[])],
        citation_ids=citation_ids,
    )


# -- extract_citation_markers -------------------------------------------


def test_extract_citation_markers_separates_well_formed_from_malformed() -> None:
    well_formed, malformed = extract_citation_markers(
        "Supported [S1, S2] but also [1, 2, 3] and [s 1]."
    )

    assert well_formed == {"S1", "S2"}
    assert malformed == {"1", "2", "3", "s 1"}


def test_extract_citation_markers_on_plain_text_finds_nothing() -> None:
    well_formed, malformed = extract_citation_markers("No brackets here at all.")

    assert well_formed == set()
    assert malformed == set()


# -- check_citation_validity (strict core) -------------------------------


def test_strict_core_passes_when_every_used_citation_is_known() -> None:
    report = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids={"c1", "c2"},
    )

    assert report.valid
    assert report.unknown_citation_ids == []
    assert report.fabricated_citation_rate == 0.0


def test_strict_core_flags_unsupported_citations_even_with_no_known_set() -> None:
    """
    Unlike the free-text wrapper, the strict core does NOT treat an
    empty known-citation set as "nothing to check" -- a structured
    citation_ids field citing something with zero available evidence is
    unambiguous fabrication (this is exactly review_draft()'s original
    behavior before the refactor).
    """

    report = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids=set(),
    )

    assert not report.valid
    assert report.unknown_citation_ids == ["c1"]
    assert report.fabricated_citation_rate == 1.0


def test_strict_core_with_nothing_used_and_nothing_known_is_valid() -> None:
    report = check_citation_validity(used_citation_ids=set(), known_citation_ids=set())

    assert report.valid
    assert report.fabricated_citation_rate == 0.0


def test_fabricated_citation_rate_is_the_fraction_unsupported() -> None:
    report = check_citation_validity(
        used_citation_ids={"c1", "c2", "c3", "c4"},
        known_citation_ids={"c1", "c2"},
    )

    assert report.fabricated_citation_rate == 0.5
    assert not report.valid


def test_malformed_markers_fail_syntax_check_but_not_source_existence() -> None:
    report = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids={"c1"},
        malformed_citation_markers={"s 1"},
    )

    checks_by_name = {check.check: check for check in report.checks}

    assert not checks_by_name[CitationCheckName.SYNTAX_VALIDITY].passed
    assert checks_by_name[CitationCheckName.SOURCE_EXISTENCE].passed
    # Syntax failure alone makes the overall report invalid -- it's one
    # of the four checks §8 marks release-blocking.
    assert not report.valid


def test_retrieval_provenance_only_evaluated_when_chunk_data_supplied() -> None:
    without_chunk_data = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids={"c1"},
    )
    names = {check.check for check in without_chunk_data.checks}
    assert CitationCheckName.RETRIEVAL_PROVENANCE not in names

    with_chunk_data = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids={"c1"},
        citation_chunk_ids={"c1": {"chunk-a"}},
        retrieved_chunk_ids={"chunk-a"},
    )
    names = {check.check for check in with_chunk_data.checks}
    assert CitationCheckName.RETRIEVAL_PROVENANCE in names
    assert with_chunk_data.valid


def test_retrieval_provenance_fails_when_cited_chunk_was_not_retrieved() -> None:
    """
    A citation object can claim chunk ids that a later context-
    construction step (compression, fusion) silently dropped -- this is
    exactly the failure mode EVALUATION_IMPLEMENTATION_TRACKER.md's E13
    (context-construction checks) reuses this provenance check for.
    """

    report = check_citation_validity(
        used_citation_ids={"c1"},
        known_citation_ids={"c1"},
        citation_chunk_ids={"c1": {"chunk-a"}},
        retrieved_chunk_ids={"chunk-b"},
    )

    assert not report.valid
    provenance_check = next(
        check for check in report.checks if check.check == CitationCheckName.RETRIEVAL_PROVENANCE
    )
    assert not provenance_check.passed
    assert "c1" in provenance_check.reason


# -- check_prompt_context_citation_validity (free-text wrapper) ----------


def test_wrapper_is_trivially_valid_when_prompt_context_has_no_citations() -> None:
    context = make_prompt_context(chunks=[], citations=[])

    report = check_prompt_context_citation_validity(
        content="The answer is [1, 2, 3], not a citation.",
        prompt_context=context,
    )

    assert report.valid


def test_wrapper_flags_a_citation_marker_not_in_the_prompt_context() -> None:
    context = make_prompt_context(citations=[make_citation(citation_id="S1")])

    report = check_prompt_context_citation_validity(
        content="Supported [S1]. Fabricated [S2].",
        prompt_context=context,
    )

    assert not report.valid
    assert report.unknown_citation_ids == ["S2"]
    assert report.fabricated_citation_rate == 0.5


def test_wrapper_checks_chunk_level_provenance_from_prompt_context() -> None:
    retrieved_chunk_id = uuid4()
    dropped_chunk_id = uuid4()

    context = make_prompt_context(
        chunks=[make_chunk(citation_id="S1", chunk_id=retrieved_chunk_id)],
        citations=[make_citation(citation_id="S1", chunk_ids=[dropped_chunk_id])],
    )

    report = check_prompt_context_citation_validity(
        content="Supported [S1].",
        prompt_context=context,
    )

    # S1 exists (source_existence passes) but its Citation object claims
    # a chunk that isn't in the actually-retrieved chunk list.
    assert not report.valid
    provenance_check = next(
        check for check in report.checks if check.check == CitationCheckName.RETRIEVAL_PROVENANCE
    )
    assert not provenance_check.passed


# -- review_draft() delegates to the shared core (regression coverage) ---


def test_review_draft_still_revises_on_unsupported_citations_after_refactor() -> None:
    review = review_draft(
        draft=_draft(["invented"]),
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
    )

    assert review.decision is ReviewDecision.REVISE_SYNTHESIS
    assert review.citation_integrity_score == 0


def test_review_draft_still_passes_on_fully_supported_citations_after_refactor() -> None:
    review = review_draft(
        draft=_draft(["c1"]),
        evidence=ResearchEvidenceBundle(
            citation_ids=["c1"], completed_task_count=1, failed_task_count=0
        ),
    )

    assert review.decision is ReviewDecision.PASS
    assert review.citation_integrity_score == 1


# -- Zero false positives against the golden set (E4's acceptance --------
# -- criterion, deferred until the golden set existed, per --------------
# -- EVALUATION_IMPLEMENTATION_TRACKER.md E4) -----------------------------


def _golden_examples() -> list[GoldenExample]:
    dataset = load_golden_dataset(GOLDEN_DATASET_PATH)
    return [
        example
        for example in dataset.examples
        if example.expected_behavior == ExpectedBehavior.ANSWER
    ]


def _filenames_for_contexts(example: GoldenExample) -> list[str]:
    """
    One filename per `example.contexts` entry. Most examples have a
    single `reference_context_ids` entry covering several context
    passages from that one document (every passage gets that filename);
    a handful (`s7`/`s8`) genuinely cite multiple documents, and for
    those `contexts` and `reference_context_ids` are the same length, so
    a direct 1:1 zip is correct.
    """

    if len(example.reference_context_ids) <= 1:
        filename = example.reference_context_ids[0] if example.reference_context_ids else "unknown"
        return [filename] * len(example.contexts)

    assert len(example.reference_context_ids) == len(example.contexts), (
        f"{example.example_id}: multi-document example needs contexts and "
        "reference_context_ids to be the same length to pair them up"
    )
    return list(example.reference_context_ids)


async def test_no_false_positives_against_golden_set_correctly_cited_examples() -> None:
    """
    Every one of the golden set's 101 answerable examples is, by
    construction, correctly cited: `expected_citation_ids` is always a
    subset of `reference_context_ids` (verified separately, see the
    dataset itself). Running the *real* citation-validity code path
    (`CitationService.build()` + `check_prompt_context_citation_validity()`,
    not a hand-rolled substitute) against a correctly-cited answer for
    every example must never flag a fabrication -- a false positive here
    would mean the validator blocks a real, well-supported answer in
    production.
    """

    citation_service = CitationService()
    false_positives: list[str] = []

    for example in _golden_examples():
        filenames = _filenames_for_contexts(example)

        chunks = [
            ContextChunk(
                chunk_id=uuid4(),
                document_id=uuid4(),
                filename=filename,
                owner_id="golden-set-verification",
                chunk_index=index,
                content=content,
                score=1.0,
            )
            for index, (content, filename) in enumerate(
                zip(example.contexts, filenames, strict=True)
            )
        ]

        citation_result = await citation_service.build(chunks)

        cited_markers = [
            citation.citation_id
            for citation in citation_result.citations
            if citation.filename in example.expected_citation_ids
        ]

        content = f"{example.reference_answer} " + "".join(f"[{m}]" for m in cited_markers)

        prompt_context = PromptContext(
            context="\n\n".join(example.contexts),
            chunks=chunks,
            citations=citation_result.citations,
        )

        report = check_prompt_context_citation_validity(
            content=content,
            prompt_context=prompt_context,
        )

        if not report.valid:
            false_positives.append(f"{example.example_id}: {report.model_dump()}")

    assert not false_positives, (
        f"{len(false_positives)} golden-set example(s) produced a false-positive "
        f"fabrication flag:\n" + "\n".join(false_positives)
    )
