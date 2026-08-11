"""
Cross-surface citation validity checking (EVALUATION_PLAN.md §8).

Generalizes `review_draft()`'s existence check
(`app/ai/runtime/research/review.py`) -- previously a real, deterministic
check but Deep-Research-only and never exposed outside that graph -- into
a reusable, surface-agnostic validator. Two live call sites already
implement half of this pattern independently:

- `CitationValidator` (`generation/validation/output/citation_validator.py`)
  extracts bracket-marker citations (`[S1]`) from free-text generations
  and checks them against `PromptContext` -- runs on every surface today,
  but only performs the existence check, and deliberately treats "no
  known citations at all" as a no-op to avoid false-positiving on
  non-citation brackets (a JSON array literal, a footnote-style numbered
  list) in free text that was never a citation attempt.
- `review_draft()` performs the same existence check against Deep
  Research's *structured* `citation_ids` fields, where there is no
  free-text ambiguity to hedge against -- an empty `citation_ids` field
  citing an empty evidence set is unambiguously a fabrication, not a
  parsing false positive.

`check_citation_validity()` below is the shared, strict core both those
call sites delegate to (see `citation_validator.py` and
`runtime/research/review.py`). `check_prompt_context_citation_validity()`
is the free-text-specific wrapper that reintroduces the "nothing to check
against" leniency, scoped to exactly the call sites that need it.
"""

from __future__ import annotations

import re
from enum import StrEnum

from app.ai.knowledge.context.models import PromptContext
from pydantic import BaseModel, ConfigDict, Field

_BRACKET_RE = re.compile(r"\[([^\[\]]+)\]")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z][\w.-]*$")


class CitationCheckName(StrEnum):
    """The four checks from EVALUATION_PLAN.md §8's table."""

    SYNTAX_VALIDITY = "syntax_validity"
    SOURCE_EXISTENCE = "source_existence"
    RETRIEVAL_PROVENANCE = "retrieval_provenance"
    FABRICATED_CITATION_RATE = "fabricated_citation_rate"


class CitationCheckResult(BaseModel):
    """
    Pass/fail plus a written reason, per §18's judge-output-format rule --
    "fail — cites Paper B for a claim actually made in Paper C" is
    actionable in a way a bare score never is.
    """

    model_config = ConfigDict(extra="forbid")

    check: CitationCheckName

    passed: bool

    reason: str


class CitationValidityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: list[CitationCheckResult]

    fabricated_citation_rate: float = Field(ge=0, le=1)
    """
    Fraction of used citation ids that don't resolve to a source made
    available this turn. §13's absolute regression gate targets 0% here.
    """

    valid: bool
    """True only if every check in `checks` passed."""

    known_citation_ids: list[str] = Field(default_factory=list)

    unknown_citation_ids: list[str] = Field(default_factory=list)

    unprovenanced_citation_ids: list[str] = Field(default_factory=list)
    """
    Citation ids that exist and were used, but whose claimed chunks
    weren't found in `retrieved_chunk_ids` -- empty whenever the caller
    didn't supply chunk-level data (the retrieval-provenance check didn't
    run at all, see `checks`).
    """

    malformed_citation_markers: list[str] = Field(default_factory=list)
    """
    Bracketed tokens that don't match the citation-id identifier pattern
    (e.g. "[s 1]", "[S1!]") -- reported for visibility, not blocking on
    its own. Free text legitimately contains non-citation brackets (a
    JSON array literal, a footnote-style numbered list); flagging every
    one as a hard failure would make this check noisy rather than
    actionable. See `check_prompt_context_citation_validity`'s docstring.
    """


def extract_citation_markers(
    content: str,
) -> tuple[set[str], set[str]]:
    """
    Parse bracketed citation markers out of free text (e.g. "[S1]",
    "[S1, S2]").

    Returns `(well_formed, malformed)` -- well-formed tokens match the
    citation-id identifier pattern (`CitationService.build()`'s
    `citation_id = "S{n}"` convention); malformed tokens are anything
    else found inside brackets, kept separate rather than silently
    dropped so callers that care about syntax validity (§8) can see them,
    while callers that don't (the free-text existence check, which
    tolerates non-citation brackets) can ignore them.
    """

    well_formed: set[str] = set()
    malformed: set[str] = set()

    for match in _BRACKET_RE.finditer(content):
        for raw_token in match.group(1).split(","):
            token = raw_token.strip()

            if not token:
                continue

            if _IDENTIFIER_RE.match(token):
                well_formed.add(token)
            else:
                malformed.add(token)

    return well_formed, malformed


def check_citation_validity(
    *,
    used_citation_ids: set[str],
    known_citation_ids: set[str],
    malformed_citation_markers: set[str] | None = None,
    citation_chunk_ids: dict[str, set[str]] | None = None,
    retrieved_chunk_ids: set[str] | None = None,
) -> CitationValidityReport:
    """
    Strict, surface-agnostic core. Every citation in `used_citation_ids`
    not present in `known_citation_ids` counts as unsupported -- including
    when `known_citation_ids` is empty (a citation used with zero
    available sources is unambiguously fabricated at this layer; the
    free-text leniency for "no citations were ever offered so an
    arbitrary bracket isn't evidence of anything" belongs in the caller
    that does free-text extraction, see
    `check_prompt_context_citation_validity`, not here).

    `citation_chunk_ids`/`retrieved_chunk_ids` are optional: the
    retrieval-provenance check only runs when the caller can supply
    chunk-level data. Not every surface carries it at the same
    granularity -- Deep Research's `ResearchEvidenceBundle` is a
    deliberately citation-safe format (references only, no raw chunk
    list distinct from its evidence), so its provenance check is
    tautological (evidence *is* the retrieved set); Chat/Linear
    Research's `PromptContext` carries a real, independently-checkable
    chunk list, so provenance is a meaningful check there. See
    `check_prompt_context_citation_validity`.
    """

    malformed_citation_markers = malformed_citation_markers or set()

    unknown_ids = sorted(used_citation_ids - known_citation_ids)

    fabricated_rate = len(unknown_ids) / len(used_citation_ids) if used_citation_ids else 0.0

    checks = [
        CitationCheckResult(
            check=CitationCheckName.SYNTAX_VALIDITY,
            passed=not malformed_citation_markers,
            reason=(
                "All citation markers are well-formed."
                if not malformed_citation_markers
                else (
                    f"Malformed citation marker(s): {', '.join(sorted(malformed_citation_markers))}"
                )
            ),
        ),
        CitationCheckResult(
            check=CitationCheckName.SOURCE_EXISTENCE,
            passed=not unknown_ids,
            reason=(
                "Every cited source exists in the retrieved set."
                if not unknown_ids
                else (f"Cites source(s) not present in the retrieved set: {', '.join(unknown_ids)}")
            ),
        ),
        CitationCheckResult(
            check=CitationCheckName.FABRICATED_CITATION_RATE,
            passed=fabricated_rate == 0.0,
            reason=(f"{fabricated_rate:.0%} of cited sources are fabricated (target 0%)."),
        ),
    ]

    unprovenanced: list[str] = []

    if citation_chunk_ids is not None and retrieved_chunk_ids is not None:
        unprovenanced = sorted(
            citation_id
            for citation_id in used_citation_ids & known_citation_ids
            if citation_chunk_ids.get(citation_id)
            and not (citation_chunk_ids[citation_id] & retrieved_chunk_ids)
        )

        checks.append(
            CitationCheckResult(
                check=CitationCheckName.RETRIEVAL_PROVENANCE,
                passed=not unprovenanced,
                reason=(
                    "Every cited source's chunks were retrieved this turn."
                    if not unprovenanced
                    else (
                        "Source(s) cited whose chunks were not actually "
                        f"retrieved this turn: {', '.join(unprovenanced)}"
                    )
                ),
            )
        )

    return CitationValidityReport(
        checks=checks,
        fabricated_citation_rate=fabricated_rate,
        valid=all(check.passed for check in checks),
        known_citation_ids=sorted(known_citation_ids),
        unknown_citation_ids=unknown_ids,
        unprovenanced_citation_ids=unprovenanced,
        malformed_citation_markers=sorted(malformed_citation_markers),
    )


def check_prompt_context_citation_validity(
    *,
    content: str,
    prompt_context: PromptContext,
) -> CitationValidityReport:
    """
    Cross-surface entrypoint for any response checked against a
    `PromptContext` -- Chat, Linear Research, and Deep Research's
    tool-turn generations all share this shape.

    Reintroduces the free-text-specific leniency `CitationValidator`
    already relied on: when the prompt context carried no citations at
    all, an arbitrary bracketed token in the response (a JSON array
    literal, a footnote-style list) is not evidence of a fabricated
    citation on its own, so this returns a trivially valid report rather
    than delegating to the strict core.
    """

    known_ids = {citation.citation_id for citation in prompt_context.citations}

    known_ids |= {chunk.citation_id for chunk in prompt_context.chunks if chunk.citation_id}

    if not known_ids:
        return CitationValidityReport(
            checks=[
                CitationCheckResult(
                    check=CitationCheckName.SOURCE_EXISTENCE,
                    passed=True,
                    reason="No citations were available this turn; nothing to validate.",
                )
            ],
            fabricated_citation_rate=0.0,
            valid=True,
        )

    well_formed, malformed = extract_citation_markers(content)

    citation_chunk_ids: dict[str, set[str]] = {
        citation.citation_id: {str(chunk_id) for chunk_id in citation.chunk_ids}
        for citation in prompt_context.citations
    }

    retrieved_chunk_ids: set[str] = {str(chunk.chunk_id) for chunk in prompt_context.chunks}

    return check_citation_validity(
        used_citation_ids=well_formed,
        known_citation_ids=known_ids,
        malformed_citation_markers=malformed,
        citation_chunk_ids=citation_chunk_ids,
        retrieved_chunk_ids=retrieved_chunk_ids,
    )


__all__ = [
    "CitationCheckName",
    "CitationCheckResult",
    "CitationValidityReport",
    "check_citation_validity",
    "check_prompt_context_citation_validity",
    "extract_citation_markers",
]
