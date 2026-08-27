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

Two entrypoints, split by whether a report's candidates carry
per-example detail (`GoldenSetGeneration`/`ProductionFailuresRegression`,
see `PER_EXAMPLE_SCORES_NOTE_KEY`): `load_reports_from()` excludes them
entirely (their `notes` payload is ~100x bigger than every other
benchmark's, and they already have a dedicated, DB-backed per-example
view -- `/offline-examples` + `/offline-scores`); `load_offline_summaries_from()`
is the mirror image, returning *only* those reports, with `notes`
stripped so their aggregate `metrics` (e.g. `rubric_adherence: 0.71`
across the whole run) can still surface somewhere -- the dedicated
per-example view has no place to show that number.
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


def _read_reports(reports_directory: Path) -> list[BenchmarkReport]:
    """Every readable `report.json` under `reports_directory`, one per
    subdirectory -- unfiltered. A malformed or unreadable report is
    logged and skipped rather than failing the whole dashboard."""

    if not reports_directory.is_dir():
        return []

    reports: list[BenchmarkReport] = []

    for entry in sorted(reports_directory.iterdir()):
        report_path = entry / "report.json"

        if not report_path.is_file():
            continue

        try:
            reports.append(
                BenchmarkReport.model_validate_json(report_path.read_text(encoding="utf-8"))
            )
        except Exception:
            logger.warning(
                "Skipping unreadable benchmark report: %s",
                report_path,
                exc_info=True,
            )

    return reports


def load_reports_from(reports_directory: Path) -> list[BenchmarkReport]:
    """
    One `BenchmarkReport` per subdirectory of `reports_directory` that
    has a `report.json` -- the latest run of each benchmark, exactly as
    `benchmarks/runner.py` last wrote it.
    """

    reports = [
        report for report in _read_reports(reports_directory) if not _has_per_example_detail(report)
    ]

    return sorted(reports, key=lambda report: report.benchmark_name)


def load_offline_summaries_from(reports_directory: Path) -> list[BenchmarkReport]:
    """
    The mirror image of `load_reports_from` -- only the reports *with*
    per-example detail (`GoldenSetGeneration`, `ProductionFailuresRegression`),
    which `load_reports_from` excludes entirely. Those have their own
    dedicated, DB-backed per-example view (`/offline-examples` +
    `/offline-scores`), but that view has no place to show the *aggregate*
    numbers (e.g. `rubric_adherence: 0.71` across the whole run) -- this
    fills that gap by reusing the same read-only file pattern, with
    `notes` stripped from each candidate so the response stays small (the
    per-example payload is ~100x bigger than the aggregate `metrics`
    dict alone, and the dedicated view already serves that detail).
    """

    reports = [
        report for report in _read_reports(reports_directory) if _has_per_example_detail(report)
    ]

    stripped = [
        report.model_copy(
            update={
                "candidates": [
                    candidate.model_copy(update={"notes": {}}) for candidate in report.candidates
                ]
            }
        )
        for report in reports
    ]

    return sorted(stripped, key=lambda report: report.benchmark_name)


async def list_benchmark_reports() -> list[BenchmarkReport]:
    """FastAPI dependency entrypoint -- see `load_reports_from` for the logic."""

    return load_reports_from(BENCHMARK_REPORTS_DIRECTORY)


async def list_offline_summaries() -> list[BenchmarkReport]:
    """FastAPI dependency entrypoint -- see `load_offline_summaries_from`."""

    return load_offline_summaries_from(BENCHMARK_REPORTS_DIRECTORY)
