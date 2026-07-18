"""
Generation benchmark query dataset.

Loads the ground-truth query set used to evaluate generation candidates.

Unlike the retrieval dataset, each entry carries its own `context`
directly (rather than relying on a live retrieval call) so the
generation benchmark can isolate generation quality from retrieval
quality -- the same reasoning that keeps chunking/embedding benchmarks
decoupled from later pipeline stages (see
benchmarks/datasets/README.md's canonical-artifact-per-stage table).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class GenerationBenchmarkQuery(BaseModel):
    """
    A single benchmark query with its grounding context and expected
    answer.
    """

    model_config = ConfigDict(extra="forbid")

    query_id: str

    query: str

    context: str = Field(
        description="Grounding context supplied directly to generation, bypassing retrieval.",
    )

    expected_answer: str = Field(
        description="Reference answer used to score completeness.",
    )

    citations: list[str] = Field(
        default_factory=list,
        description="Filenames the answer is expected to reference.",
    )


class GenerationQueryDataset(BaseModel):
    """
    Canonical generation benchmark query dataset.
    """

    model_config = ConfigDict(extra="forbid")

    version: str

    notes: str = ""

    queries: list[GenerationBenchmarkQuery]


def load_generation_queries(
    path: Path,
) -> GenerationQueryDataset:
    """
    Load the generation benchmark query dataset.

    Args:
        path:
            Path to the generation_queries.json file.

    Raises:
        FileNotFoundError:
            If the query dataset file does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(f"Generation query dataset not found: {path}")

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return GenerationQueryDataset.model_validate(payload)
