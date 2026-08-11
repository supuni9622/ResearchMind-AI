"""
Reads `benchmarks/reports/*/report.json` off disk for the internal eval
dashboard (E7 follow-up, EVALUATION_IMPLEMENTATION_TRACKER.md).

Deliberate app/`benchmarks` boundary crossing -- the same kind of
crossing `bootstrap/worker.py` already makes for the Ragas judge, kept
here rather than spread through `app/ai/...` because this is purely a
read-only view over files `benchmarks/runner.py` already writes;
nothing here touches the database.

Report freshness is whatever's on disk from the last `python -m
benchmarks.runner <name> --dataset ...` run -- there is no persistence
or trend history here, unlike `GoldenSetBenchmark`'s `eval_scores` rows.
Any report whose candidates carry per-example detail (currently only
`GoldenSetGeneration`, see `PER_EXAMPLE_SCORES_NOTE_KEY`) is skipped:
that one already has its own dedicated, DB-backed view
(`/offline-examples` + `/offline-scores`), and its `notes` payload is
~100x bigger than every other benchmark's.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.constants import BENCHMARK_REPORTS_DIRECTORY
from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY
from benchmarks.models.report import BenchmarkReport

logger = logging.getLogger(__name__)


def _has_per_example_detail(report: BenchmarkReport) -> bool:
    return any(PER_EXAMPLE_SCORES_NOTE_KEY in candidate.notes for candidate in report.candidates)


def load_reports_from(reports_directory: Path) -> list[BenchmarkReport]:
    """
    One `BenchmarkReport` per subdirectory of `reports_directory` that
    has a `report.json` -- the latest run of each benchmark, exactly as
    `benchmarks/runner.py` last wrote it. A malformed or unreadable
    `report.json` is logged and skipped rather than failing the whole
    dashboard.
    """

    if not reports_directory.is_dir():
        return []

    reports: list[BenchmarkReport] = []

    for entry in sorted(reports_directory.iterdir()):
        report_path = entry / "report.json"

        if not report_path.is_file():
            continue

        try:
            report = BenchmarkReport.model_validate_json(report_path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "Skipping unreadable benchmark report: %s",
                report_path,
                exc_info=True,
            )
            continue

        if _has_per_example_detail(report):
            continue

        reports.append(report)

    return sorted(reports, key=lambda report: report.benchmark_name)


async def list_benchmark_reports() -> list[BenchmarkReport]:
    """FastAPI dependency entrypoint -- see `load_reports_from` for the logic."""

    return load_reports_from(BENCHMARK_REPORTS_DIRECTORY)
