"""
Golden-set generation benchmark (EVALUATION_PLAN.md §7's release-candidate
tier, §13's "release candidate -> full regression suite" trigger, E6).

Distinct from `GenerationBenchmark` (`benchmarks/generation/benchmark.py`),
which scores every candidate provider against `generation_queries.json`
using cheap lexical-overlap proxies and no LLM judge, for CI-smoke speed.
This benchmark instead runs the real `rag_answer_gold` golden dataset
(115 hand-verified examples, `benchmarks/generation/golden_dataset.py`)
through a live generation call and the real Ragas judge
(`benchmarks/generation/ragas_scoring.score_generation()`,
`ragas_judge.build_openai_ragas_judge()`) -- E1 built the scoring
function and the dataset, but nothing runnable ever exercised them
together outside a single pytest test using a fake judge. This is that
missing runner.

Expensive by design, not meant for every-PR CI: one real generation call
plus up to 4 real Ragas judge calls per example per provider. Intended
for the release-candidate tier only.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.service import GenerationService

from benchmarks.common.metrics import average
from benchmarks.generation.golden_dataset import (
    ExpectedBehavior,
    GoldenExample,
    load_golden_dataset,
)
from benchmarks.generation.ragas_scoring import GenerationJudge, score_generation
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

GOLDEN_DATASET_FILENAME = "rag_answer_gold.json"

BENCHMARK_OWNER_ID = "benchmark"

PER_EXAMPLE_SCORES_NOTE_KEY = "per_example_scores"
"""
`BenchmarkCandidate.notes[...]` key holding this run's per-example detail
-- a list of `{"example_id", "metric", "score", "passed", "reason"}`
dicts. `BenchmarkReport`/`BenchmarkCandidate` are shared across every
benchmark and deliberately stay aggregate-only (see their own module
docstring); `notes: dict[str, Any]` is the existing, already-generic
escape hatch other benchmarks use for extra per-run detail (e.g.
`GenerationBenchmark`'s `error` note), not a new mechanism invented here.
`persist_golden_set_scores.py` is the only reader of this key.
"""


class GoldenSetBenchmark(Benchmark):
    """
    Runs `rag_answer_gold`'s answerable examples through a live
    generation call per configured provider, then scores each with the
    real Ragas judge suite.
    """

    def __init__(
        self,
        *,
        registry: GenerationRegistry,
        generation_service: GenerationService,
        judge: GenerationJudge,
    ) -> None:
        self._registry = registry
        self._generation_service = generation_service
        self._judge = judge

    @property
    def name(self) -> str:
        return "GoldenSetGeneration"

    async def run(self, dataset_path: Path) -> BenchmarkReport:
        dataset = load_golden_dataset(dataset_path / GOLDEN_DATASET_FILENAME)

        answerable = [
            example
            for example in dataset.examples
            if example.expected_behavior == ExpectedBehavior.ANSWER
        ]

        candidates = [
            await self._evaluate(provider, answerable) for provider in self._registry.providers
        ]

        model_versions = {
            candidate.name: candidate.version for candidate in candidates if candidate.version
        }

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(answerable),
            ),
            metadata=BenchmarkMetadata(
                dataset_version=dataset.version,
                model_versions=model_versions,
            ),
            candidates=candidates,
        )

    async def _evaluate(
        self,
        provider: GenerationProvider,
        examples: list[GoldenExample],
    ) -> BenchmarkCandidate:
        """
        Run every answerable golden example through one candidate
        provider, score each with the real Ragas judge, and aggregate.

        A single example's failure (provider error, judge error) is
        recorded in that example's own per-example entry rather than
        aborting the whole candidate -- mirrors `GenerationBenchmark`'s
        "one candidate failing shouldn't sink the whole report" instinct,
        applied at example granularity instead of candidate granularity
        since a golden-set run has ~100x more individual calls that can
        fail transiently.
        """

        per_example: list[dict[str, object]] = []
        metric_scores: dict[str, list[float]] = {}
        model: str | None = None
        candidate_error: str | None = None

        try:
            for example in examples:
                source_filename = (
                    example.reference_context_ids[0]
                    if example.reference_context_ids
                    else "benchmark"
                )
                tagged_context = "\n\n".join(example.contexts)

                request = GenerationRequest(
                    prompt_context=PromptContext(
                        context=tagged_context,
                        chunks=[
                            ContextChunk(
                                chunk_id=uuid4(),
                                document_id=uuid4(),
                                filename=source_filename,
                                owner_id=BENCHMARK_OWNER_ID,
                                chunk_index=0,
                                content=chunk_content,
                                score=1.0,
                            )
                            for chunk_content in example.contexts
                        ],
                    ),
                    user_prompt=example.question,
                )

                try:
                    result = await self._generation_service.generate(
                        request=request,
                        provider=provider,
                    )
                    model = result.model

                    report = await score_generation(
                        question=example.question,
                        answer=result.content,
                        contexts=example.contexts,
                        reference=example.reference_answer,
                        judge=self._judge,
                    )

                    for check in report.checks:
                        metric_scores.setdefault(check.metric, []).append(check.score)
                        per_example.append(
                            {
                                "example_id": example.example_id,
                                "metric": check.metric,
                                "score": check.score,
                                "passed": check.passed,
                                "reason": check.reason,
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    # This example's own failure (provider error, judge
                    # error) -- recorded per-example, doesn't abort the run.
                    per_example.append(
                        {
                            "example_id": example.example_id,
                            "metric": "error",
                            "score": None,
                            "passed": False,
                            "reason": str(exc),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            # Something broke outside the per-example loop itself (e.g.
            # provider registry lookup) -- the whole candidate failed.
            candidate_error = str(exc)

        metrics: dict[str, float | int | str | bool] = {
            "examples_evaluated": len(examples),
            **{metric_name: average(scores) for metric_name, scores in metric_scores.items()},
        }

        notes: dict[str, object] = {PER_EXAMPLE_SCORES_NOTE_KEY: per_example}
        if candidate_error is not None:
            notes["error"] = candidate_error

        return BenchmarkCandidate(
            name=provider.value,
            version=model,
            metrics=metrics,
            notes=notes,
        )
