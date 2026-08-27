"""
Unit tests for `app.services.benchmark_reports.load_reports_from` (E7
follow-up, EVALUATION_IMPLEMENTATION_TRACKER.md) -- the pure
directory-scanning logic behind `GET /eval-dashboard/benchmark-reports`.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.benchmark_reports import load_offline_summaries_from, load_reports_from

from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY


def _write_report(directory: Path, *, benchmark_name: str, notes: dict | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    report = {
        "benchmark_name": benchmark_name,
        "dataset": {"name": "fixtures", "document_count": 1},
        "candidates": [
            {
                "name": "candidate-a",
                "metrics": {"recall_at_5": 0.9},
                "notes": notes or {},
            },
        ],
    }
    (directory / "report.json").write_text(json.dumps(report), encoding="utf-8")


def test_missing_directory_returns_empty_list(tmp_path: Path) -> None:
    assert load_reports_from(tmp_path / "does-not-exist") == []


def test_loads_one_report_per_subdirectory(tmp_path: Path) -> None:
    _write_report(tmp_path / "embeddings", benchmark_name="Embeddings")
    _write_report(tmp_path / "retrieval", benchmark_name="Retrieval")

    reports = load_reports_from(tmp_path)

    assert [report.benchmark_name for report in reports] == ["Embeddings", "Retrieval"]


def test_skips_subdirectory_with_no_report_json(tmp_path: Path) -> None:
    (tmp_path / "empty-dir").mkdir()
    _write_report(tmp_path / "embeddings", benchmark_name="Embeddings")

    reports = load_reports_from(tmp_path)

    assert [report.benchmark_name for report in reports] == ["Embeddings"]


def test_skips_malformed_report_json(tmp_path: Path) -> None:
    malformed = tmp_path / "broken"
    malformed.mkdir()
    (malformed / "report.json").write_text("{not valid json", encoding="utf-8")
    _write_report(tmp_path / "embeddings", benchmark_name="Embeddings")

    reports = load_reports_from(tmp_path)

    assert [report.benchmark_name for report in reports] == ["Embeddings"]


def test_skips_reports_with_per_example_detail(tmp_path: Path) -> None:
    """GoldenSetGeneration already has its own dedicated, DB-backed
    offline-examples/offline-scores view -- it should not also show up
    in this generic file-based listing."""

    _write_report(
        tmp_path / "goldensetgeneration",
        benchmark_name="GoldenSetGeneration",
        notes={PER_EXAMPLE_SCORES_NOTE_KEY: [{"example_id": "g1"}]},
    )
    _write_report(tmp_path / "embeddings", benchmark_name="Embeddings")

    reports = load_reports_from(tmp_path)

    assert [report.benchmark_name for report in reports] == ["Embeddings"]


# -- load_offline_summaries_from (mirror image) -----------------------------


def test_offline_summaries_returns_only_reports_with_per_example_detail(tmp_path: Path) -> None:
    _write_report(
        tmp_path / "goldensetgeneration",
        benchmark_name="GoldenSetGeneration",
        notes={PER_EXAMPLE_SCORES_NOTE_KEY: [{"example_id": "g1"}]},
    )
    _write_report(tmp_path / "embeddings", benchmark_name="Embeddings")

    reports = load_offline_summaries_from(tmp_path)

    assert [report.benchmark_name for report in reports] == ["GoldenSetGeneration"]


def test_offline_summaries_strips_notes_but_keeps_metrics(tmp_path: Path) -> None:
    _write_report(
        tmp_path / "goldensetgeneration",
        benchmark_name="GoldenSetGeneration",
        notes={PER_EXAMPLE_SCORES_NOTE_KEY: [{"example_id": "g1", "metric": "faithfulness"}]},
    )

    reports = load_offline_summaries_from(tmp_path)

    candidate = reports[0].candidates[0]
    assert candidate.notes == {}
    assert candidate.metrics == {"recall_at_5": 0.9}


def test_missing_directory_returns_empty_offline_summaries(tmp_path: Path) -> None:
    assert load_offline_summaries_from(tmp_path / "does-not-exist") == []
