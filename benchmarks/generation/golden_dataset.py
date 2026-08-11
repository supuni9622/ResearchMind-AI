"""
Golden dataset for generation evaluation (EVALUATION_PLAN.md §3, `rag_answer_gold`).

Per-example schema adopted as-is from §3 -- rich enough fields on each
example that one dataset can be sliced by `query_type`/`workflow` for
reporting, instead of needing a dozen separate tables kept in sync
independently. This repo owns schema/versioning (per §1's RAGAS/LangSmith/
ResearchMind-code split); the dataset itself is registered in LangSmith
as the primary registry once volume justifies the round-trip.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class QueryType(StrEnum):
    FACTUAL = "factual"
    SYNTHESIS = "synthesis"
    COMPARISON = "comparison"
    EXPLORATORY = "exploratory"
    UNANSWERABLE = "unanswerable"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Workflow(StrEnum):
    CHAT = "chat"
    LINEAR_RESEARCH = "linear_research"
    DEEP_RESEARCH = "deep_research"


class ExpectedBehavior(StrEnum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    REFUSE = "refuse"
    ABSTAIN = "abstain"
    CONTINUE_RESEARCH = "continue_research"


class GoldenExample(BaseModel):
    """One `rag_answer_gold` example (EVALUATION_PLAN.md §3's schema table)."""

    model_config = ConfigDict(extra="forbid")

    example_id: str

    question: str

    reference_answer: str | None = Field(
        default=None,
        description="Human-approved expected answer, where applicable.",
    )

    reference_context_ids: list[str] = Field(
        default_factory=list,
        description="Known relevant chunks/documents (here: source filenames).",
    )

    required_claims: list[str] = Field(default_factory=list)

    forbidden_claims: list[str] = Field(default_factory=list)

    expected_citation_ids: list[str] = Field(default_factory=list)

    expected_behavior: ExpectedBehavior = ExpectedBehavior.ANSWER

    query_type: QueryType

    difficulty: Difficulty

    workflow: Workflow

    metadata_filters: dict[str, str] = Field(default_factory=dict)

    rubric: str | None = Field(
        default=None,
        description="Example-specific evaluation criteria, for LLM-judge cases.",
    )

    expected_tool: str | None = Field(
        default=None,
        description="Correct tool/action for this turn (web_search, paper_search, or none).",
    )

    expected_route: str | None = Field(
        default=None,
        description="Correct Deep Research workflow path, where applicable.",
    )

    failure_category: str | None = Field(
        default=None,
        description=(
            "Set only for examples promoted from `production_failures` "
            "(EVALUATION_PLAN.md §3's failure_category taxonomy)."
        ),
    )

    # Retrieval-grounding context, kept alongside the example so the
    # generation scoring function can run without a live retrieval call --
    # see EVALUATION_PLAN.md §7: the RAG suite needs (question, contexts,
    # answer[, reference]) as inputs.
    contexts: list[str] = Field(
        default_factory=list,
        description="Verbatim context passages this example's answer should be grounded in.",
    )


class GoldenDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str

    notes: str = ""

    examples: list[GoldenExample]


def load_golden_dataset(path: Path) -> GoldenDataset:
    """
    Load `rag_answer_gold` from disk.

    Raises:
        FileNotFoundError:
            If the dataset file does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(f"Golden dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    return GoldenDataset.model_validate(payload)
