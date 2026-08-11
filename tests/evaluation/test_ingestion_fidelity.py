"""
Ingestion fidelity contract (EVALUATION_PLAN.md §4, §18 Level 1).

Named home for §4's ingestion checks -- like citation validity (E4), this
doesn't map onto any of the six originally-named stub files, so it gets
its own file rather than overloading an unrelated one (see
`test_citation_validity.py`'s docstring for the same correction).

Unlike `tests/unit/benchmarks/ingestion/test_metrics.py` (isolated,
hand-constructed Markdown strings), this runs the actual
`IngestionFidelityBenchmark` against the real fixture set
(`benchmarks/datasets/research-papers/ingestion_fidelity_fixtures.json` +
each fixture's real Docling-parsed `processed_document.json`), so it
would catch a regression in the fixture data itself, not just in the
metric formulas.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks.ingestion.benchmark import IngestionFidelityBenchmark
from benchmarks.ingestion.fixtures import load_fixture_manifest

DATASET_PATH = Path(__file__).resolve().parents[2] / "benchmarks" / "datasets" / "research-papers"


def test_fixture_manifest_is_non_empty() -> None:
    manifest = load_fixture_manifest(DATASET_PATH)

    assert len(manifest.fixtures) >= 3


def test_every_fixture_expects_at_least_one_heading_and_one_table() -> None:
    """
    Confirms the fixture set actually covers what EVALUATION_PLAN.md §4
    asks for -- "heading hierarchy + at least one table-bearing
    document" -- not just that the manifest parses.
    """

    manifest = load_fixture_manifest(DATASET_PATH)

    for fixture in manifest.fixtures:
        assert fixture.expected_min_headings >= 1, fixture.document_dir
        assert fixture.expected_min_tables >= 1, fixture.document_dir


@pytest.mark.asyncio
async def test_benchmark_scores_the_real_fixture_set_at_full_fidelity() -> None:
    """
    Running the benchmark against its own real fixtures should score
    1.0 across the board -- the minimums were derived directly from
    this same data. A score below 1.0 here means either the fixture
    data or the manifest has drifted out of sync, which this test
    exists specifically to catch.
    """

    report = await IngestionFidelityBenchmark().run(DATASET_PATH)

    assert len(report.candidates) == 1
    metrics = report.candidates[0].metrics

    assert metrics["parse_success_rate"] == 1.0
    assert metrics["heading_preservation_score"] == 1.0
    assert metrics["table_preservation_score"] == 1.0


@pytest.mark.asyncio
async def test_benchmark_raises_when_the_fixture_manifest_is_missing() -> None:
    with pytest.raises(FileNotFoundError):
        await IngestionFidelityBenchmark().run(Path(__file__).resolve().parent)


@pytest.mark.asyncio
async def test_benchmark_scores_a_missing_fixture_document_as_a_parse_failure(
    tmp_path: Path,
) -> None:
    """
    Points the benchmark at a manifest that references a fixture whose
    `processed_document.json` doesn't exist -- exercising the "document
    fails ingestion outright" path deterministically, without depending
    on Docling actually failing on real input.
    """

    manifest = {
        "version": "1.0",
        "notes": "test fixture",
        "fixtures": [
            {
                "document_dir": "missing-paper",
                "filename": "missing.pdf",
                "expected_min_headings": 1,
                "expected_min_tables": 1,
            }
        ],
    }
    (tmp_path / "ingestion_fidelity_fixtures.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    report = await IngestionFidelityBenchmark().run(tmp_path)

    metrics = report.candidates[0].metrics
    assert metrics["parse_success_rate"] == 0.0
    assert metrics["heading_preservation_score"] == 0.0
    assert metrics["table_preservation_score"] == 0.0
