"""
Retrieval benchmark query dataset.

Loads the ground-truth query set used to evaluate retrieval candidates.

Relevance is currently judged at document level (a retrieved chunk
counts as a hit if its source document filename is listed as relevant).
Chunk-level relevance is a possible future refinement once document-level
evaluation has proven useful.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RetrievalBenchmarkQuery(BaseModel):
    """
    A single benchmark query with its ground-truth relevant documents.
    """

    model_config = ConfigDict(extra="forbid")

    query_id: str

    query: str

    category: str = Field(
        description="Query category, e.g. semantic, acronym, exact_keyword, code_entity.",
    )

    relevant_documents: list[str] = Field(
        description="Filenames of documents considered relevant to this query.",
    )


class RetrievalQueryDataset(BaseModel):
    """
    Canonical retrieval benchmark query dataset.
    """

    model_config = ConfigDict(extra="forbid")

    version: str

    relevance_level: str

    notes: str = ""

    queries: list[RetrievalBenchmarkQuery]


def load_retrieval_queries(
    path: Path,
) -> RetrievalQueryDataset:
    """
    Load the retrieval benchmark query dataset.

    Args:
        path:
            Path to the retrieval_queries.json file.

    Raises:
        FileNotFoundError:
            If the query dataset file does not exist.
    """

    if not path.exists():
        raise FileNotFoundError(f"Retrieval query dataset not found: {path}")

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        payload = json.load(file)

    return RetrievalQueryDataset.model_validate(payload)
