"""
Unit tests for the retrieval benchmark query dataset loader.

Covers:
- A well-formed dataset file loads into typed query objects
- Loading a missing file raises FileNotFoundError
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.retrieval.dataset import load_retrieval_queries


def _write_dataset(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "version": "1.0",
                "relevance_level": "document",
                "notes": "test dataset",
                "queries": [
                    {
                        "query_id": "q1",
                        "query": "What is BSE?",
                        "category": "acronym",
                        "relevant_documents": ["paper.pdf"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def test_load_retrieval_queries_parses_a_well_formed_dataset(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "retrieval_queries.json"
    _write_dataset(dataset_path)

    dataset = load_retrieval_queries(dataset_path)

    assert dataset.version == "1.0"
    assert len(dataset.queries) == 1
    assert dataset.queries[0].query_id == "q1"
    assert dataset.queries[0].relevant_documents == ["paper.pdf"]


def test_load_retrieval_queries_raises_for_a_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        load_retrieval_queries(tmp_path / "does_not_exist.json")
