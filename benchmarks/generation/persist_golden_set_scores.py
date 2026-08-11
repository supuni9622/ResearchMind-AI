"""
Persists a `GoldenSetGeneration` benchmark run's per-example results into
`eval_scores` (E6, EVALUATION_PLAN.md §16 phase 6/7).

Deliberately separate from `benchmarks/runner.py`: the generic runner is
file-only by design (no benchmark needs a database to produce a
`report.json` -- confirmed empirically, see `EVALUATION_IMPLEMENTATION_TRACKER.md`
E6), and this script is the one exception that does. Run it as an
explicit second step, after a `GoldenSetGeneration` run has already
written its `report.json`:

    python -m benchmarks.runner GoldenSetGeneration --dataset datasets/golden
    python -m benchmarks.generation.persist_golden_set_scores \\
        --report benchmarks/reports/goldensetgeneration/report.json
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.db.session import SessionFactory
from app.repositories.eval_score import EvalScoreRepository
from pydantic import BaseModel, ConfigDict

from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY
from benchmarks.models.report import BenchmarkReport


class PerExampleScoreEntry(BaseModel):
    """Structural mirror of the dicts `GoldenSetBenchmark` stashes under
    `BenchmarkCandidate.notes[PER_EXAMPLE_SCORES_NOTE_KEY]`."""

    model_config = ConfigDict(extra="ignore")

    example_id: str
    metric: str
    score: float | None
    passed: bool | None
    reason: str | None


def extract_offline_scores(report: BenchmarkReport) -> list[PerExampleScoreEntry]:
    """
    Pure extraction, no I/O -- flattens every candidate's per-example
    notes into one list, dropping placeholder `"error"` entries (an
    example that failed to generate/score has no metric score worth
    persisting, only a reason it's missing one).
    """

    entries: list[PerExampleScoreEntry] = []
    for candidate in report.candidates:
        raw_entries = candidate.notes.get(PER_EXAMPLE_SCORES_NOTE_KEY, [])
        for raw in raw_entries:
            entry = PerExampleScoreEntry.model_validate(raw)
            if entry.metric == "error":
                continue
            entries.append(entry)
    return entries


async def persist(
    report: BenchmarkReport,
    *,
    repository: EvalScoreRepository,
) -> int:
    """Writes every extracted entry via `record_offline_example()` (append-only,
    no conflict handling -- see that method's own docstring). Returns the
    count written. Caller owns the session/commit boundary."""

    entries = extract_offline_scores(report)
    for entry in entries:
        await repository.record_offline_example(
            dataset_example_id=entry.example_id,
            metric_name=entry.metric,
            score=entry.score,
            passed=entry.passed,
            reason=entry.reason,
        )
    return len(entries)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        required=True,
        type=Path,
        help="Path to a GoldenSetGeneration report.json.",
    )
    args = parser.parse_args()

    report = BenchmarkReport.model_validate_json(args.report.read_text(encoding="utf-8"))

    async with SessionFactory() as session:
        count = await persist(report, repository=EvalScoreRepository(session))
        await session.commit()

    print(f"Persisted {count} offline eval_scores rows from {args.report}")


if __name__ == "__main__":
    asyncio.run(main())
