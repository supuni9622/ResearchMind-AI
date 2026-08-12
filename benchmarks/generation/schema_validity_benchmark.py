"""
Schema-validity regression benchmark (`EVALUATION_PLAN.md` §13's fourth
absolute gate, `schema_validity_rate` -- declared in `thresholds.py`
alongside `abstention_pass_rate`, both never previously populated by any
benchmark run: `rag_answer_gold` is a free-text Q&A dataset with no field
carrying "the structured-output schema this example was supposed to
conform to," so `GoldenSetBenchmark`'s model can't measure this at all --
see `production_failures_benchmark.py`'s own docstring for why
`schema_violation` stays excluded from that benchmark for the identical
reason.

Exercises `ResearchPlanner.plan()` (`app/ai/runtime/research/planner/
service.py`) -- the platform's clearest real structured-output contract:
one LLM call per query, provider-enforced `response_format=STRUCTURED,
output_model=ResearchPlan` (native OpenAI strict-mode JSON schema /
Claude schema-constrained decoding, see `providers/helpers/structured.py`),
already used unmodified by production Deep Research. No golden dataset
with reference answers is needed -- `schema_validity_rate` measures
whether the raw output conforms to `ResearchPlan`, not answer quality, so
`schema_validity_dataset.py`'s query set carries no expected output at
all.

`ResearchPlanner.plan()` raises `ResearchPlannerError` for two distinct
reasons (see its own source): the parsed output failed
`ResearchPlan.model_validate()` (the actual schema-invalidity case this
benchmark exists to catch), or a *schema-valid* plan exceeded
`ResearchPlanningPolicy`'s task-count budget (a policy failure, not a
schema one). Conflating the two would understate `schema_validity_rate`
for a reason this metric doesn't claim to measure, so `_evaluate_one()`
distinguishes them by the exception's message -- coupled to the literal
string `ResearchPlanner` raises on schema failure
(`_SCHEMA_INVALID_MESSAGE` below); `test_planner.py`'s own
`match="schema-valid"` assertion is the existing tripwire if that string
ever changes.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from app.ai.runtime.research.planner.service import ResearchPlanner, ResearchPlannerError

from benchmarks.common.metrics import average
from benchmarks.generation.schema_validity_dataset import (
    SchemaValidityQuery,
    load_schema_validity_dataset,
)
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

SCHEMA_VALIDITY_DATASET_FILENAME = "schema_validity_queries.json"

DEFAULT_MAX_CONCURRENCY = 5

_SCHEMA_INVALID_MESSAGE = "Planner did not return a schema-valid plan."
"""Must match `ResearchPlannerError`'s literal message in
`planner/service.py` verbatim -- see this module's own docstring."""


class SchemaValidityBenchmark(Benchmark):
    """
    Runs each query in `schema_validity_queries.json` through
    `ResearchPlanner.plan()` and records whether the model's output was
    schema-valid. Bounded concurrency, same pattern as
    `GoldenSetBenchmark`.
    """

    def __init__(
        self,
        *,
        planner: ResearchPlanner,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._planner = planner
        self._max_concurrency = max_concurrency

    @property
    def name(self) -> str:
        return "SchemaValidityRegression"

    async def run(self, dataset_path: Path) -> BenchmarkReport:
        dataset = load_schema_validity_dataset(dataset_path / SCHEMA_VALIDITY_DATASET_FILENAME)

        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def _bounded(query: SchemaValidityQuery) -> dict[str, object]:
            async with semaphore:
                return await self._evaluate_one(query)

        per_example = await asyncio.gather(*(_bounded(query) for query in dataset.queries))

        metric_scores: dict[str, list[float]] = {}
        for entry in per_example:
            score = entry["score"]
            if entry["metric"] != "error" and isinstance(score, int | float):
                metric_scores.setdefault(str(entry["metric"]), []).append(float(score))

        metrics: dict[str, float | int | str | bool] = {
            "examples_evaluated": len(dataset.queries),
            **{metric_name: average(scores) for metric_name, scores in metric_scores.items()},
        }

        candidate = BenchmarkCandidate(
            name="planner",
            metrics=metrics,
            notes={"per_example_scores": list(per_example)},
        )

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(dataset.queries),
            ),
            metadata=BenchmarkMetadata(dataset_version=dataset.version),
            candidates=[candidate],
        )

    async def _evaluate_one(self, query: SchemaValidityQuery) -> dict[str, object]:
        try:
            await self._planner.plan(
                query=query.query,
                owner_id=uuid4(),
                research_run_id=uuid4(),
            )
        except ResearchPlannerError as exc:
            if _SCHEMA_INVALID_MESSAGE not in str(exc):
                # Schema-valid plan, rejected for an unrelated policy
                # reason (task-count budget) -- not what this metric
                # measures.
                return {
                    "example_id": query.query_id,
                    "metric": "schema_validity_rate",
                    "score": 1.0,
                    "passed": True,
                    "reason": f"schema valid; rejected for a non-schema reason: {exc}",
                }
            return {
                "example_id": query.query_id,
                "metric": "schema_validity_rate",
                "score": 0.0,
                "passed": False,
                "reason": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "example_id": query.query_id,
                "metric": "error",
                "score": None,
                "passed": False,
                "reason": f"planner call failed: {exc}",
            }

        return {
            "example_id": query.query_id,
            "metric": "schema_validity_rate",
            "score": 1.0,
            "passed": True,
            "reason": "schema-valid plan returned",
        }


__all__ = ["SchemaValidityBenchmark"]
