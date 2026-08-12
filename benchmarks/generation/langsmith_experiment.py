"""
Log a `GoldenSetBenchmark`/`ProductionFailuresBenchmark` run as a
LangSmith Experiment (E19's remaining subtask, `EVALUATION_IMPLEMENTATION_TRACKER.md`).

`langsmith_sync.py` registers the dataset once; this is the missing
other half -- each `GoldenSetGeneration` run becomes its own named
Experiment *linked to that dataset*, so successive runs are comparable
over time in LangSmith's own UI (per-metric trend across runs), not just
a point-in-time pass/fail in a local `report.json`.

One LangSmith run per golden example (not per metric -- a run is "what
happened for this example", matching the dataset's own one-example-one-row
shape), linked to its dataset example via `reference_example_id` (the
same deterministic `uuid5` mapping `langsmith_sync.py` already uses, so
LangSmith's UI can show this run's output next to that example's
reference answer). Every computed metric for that example is attached as
real `create_feedback()` scores on the run, reusing the exact
key-per-metric pattern `eval_score_sync.py`/`user_feedback.py` already
established -- so the Experiment view's per-metric columns populate the
same way LangSmith's own `evaluate()` helper would produce them, even
though this doesn't use that helper (this project's own benchmark
orchestration already does the generation + scoring; this module only
needs to *report* the result, not re-run anything).

Deliberately doesn't carry the example's actual generated answer text as
the run's `outputs` -- `BenchmarkReport`'s per-example notes are
score-only (question/answer text was a deliberate scope decision to keep
that payload from growing further, see `golden_set_benchmark.py`'s own
`PER_EXAMPLE_SCORES_NOTE_KEY` docstring) -- so `outputs` here is a
pass/fail summary plus the metric scores themselves, not a transcript.
The dataset example (already synced) already carries the question/
reference answer for side-by-side comparison in LangSmith's UI.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import structlog
from app.ai.observability.providers.langsmith.client import get_langsmith_client

from benchmarks.generation.golden_set_benchmark import PER_EXAMPLE_SCORES_NOTE_KEY
from benchmarks.generation.langsmith_sync import (
    DATASET_NAME,
    LangSmithNotConfiguredError,
    example_id_to_langsmith_id,
)
from benchmarks.models.report import BenchmarkReport

logger = structlog.get_logger()


def _group_by_example(per_example: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in per_example:
        grouped.setdefault(str(entry["example_id"]), []).append(entry)
    return grouped


def log_experiment(
    report: BenchmarkReport,
    *,
    dataset_name: str = DATASET_NAME,
    experiment_name: str | None = None,
) -> str:
    """
    Log `report` (a `GoldenSetBenchmark`/`ProductionFailuresBenchmark`
    result carrying `PER_EXAMPLE_SCORES_NOTE_KEY` notes) as a new
    LangSmith Experiment linked to `dataset_name`. Returns the created
    experiment (project) name.

    Raises:
        LangSmithNotConfiguredError: no `LANGSMITH_API_KEY` configured.
        ValueError: `report` has no per-example scores to log (wrong
            report shape -- an engineering-benchmark report, not one of
            the two this module is for).
    """

    client = get_langsmith_client()
    if client is None:
        raise LangSmithNotConfiguredError(
            "LangSmith is not configured (LANGSMITH_API_KEY unset) -- cannot log an experiment."
        )

    if not report.candidates:
        raise ValueError(f"Report for {report.benchmark_name!r} has no candidates to log.")

    candidate = report.candidates[0]
    per_example = candidate.notes.get(PER_EXAMPLE_SCORES_NOTE_KEY)
    if not per_example:
        raise ValueError(
            f"Report for {report.benchmark_name!r} has no per-example scores "
            f"(expected notes[{PER_EXAMPLE_SCORES_NOTE_KEY!r}]) -- wrong report shape."
        )

    dataset = client.read_dataset(dataset_name=dataset_name)

    name = experiment_name or f"{report.benchmark_name}-{report.generated_at:%Y-%m-%dT%H-%M-%S}"
    client.create_project(
        project_name=name,
        reference_dataset_id=dataset.id,
        metadata={
            "benchmark_name": report.benchmark_name,
            "candidate_name": candidate.name,
            "candidate_version": candidate.version,
        },
    )

    for example_id, entries in _group_by_example(per_example).items():
        scored = [entry for entry in entries if entry["metric"] != "error"]
        passed = all(entry["passed"] for entry in scored) if scored else False

        run_id = uuid4()
        client.create_run(
            id=run_id,
            name=example_id,
            run_type="chain",
            project_name=name,
            reference_example_id=example_id_to_langsmith_id(example_id),
            inputs={"example_id": example_id},
            outputs={
                "passed": passed,
                "metrics": {entry["metric"]: entry["score"] for entry in scored},
            },
            start_time=report.generated_at,
            end_time=report.generated_at,
        )

        for entry in scored:
            client.create_feedback(
                run_id=run_id,
                key=str(entry["metric"]),
                score=entry["score"],
                comment=str(entry["reason"]),
            )

    example_count = len(_group_by_example(per_example))
    logger.info(
        "langsmith_experiment.logged",
        experiment_name=name,
        dataset_name=dataset_name,
        example_count=example_count,
    )
    return name


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True, help="Path to a report.json.")
    parser.add_argument("--dataset-name", default=DATASET_NAME)
    parser.add_argument("--experiment-name", default=None)
    args = parser.parse_args()

    loaded_report = BenchmarkReport.model_validate_json(args.report.read_text(encoding="utf-8"))
    created_name = log_experiment(
        loaded_report,
        dataset_name=args.dataset_name,
        experiment_name=args.experiment_name,
    )
    print(f"Logged LangSmith Experiment '{created_name}' against dataset '{args.dataset_name}'.")
