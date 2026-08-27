"""
Production-failures regression benchmark (closes E10's "both directions"
loop for real, EVALUATION_PLAN.md §15 -- the "Evaluation Platform Gap 2"
follow-up).

`production_failures.json` (E10's confirmed-failure sync target) had no
reader anywhere until this file: `GoldenSetBenchmark` only ever loaded
`rag_answer_gold.json`, so a confirmed failure landed in the dataset file
but was never re-exercised by any future release-candidate run -- E10's
"both directions" promise only actually closed for the "good" direction.

Reuses `GoldenSetBenchmark`'s machinery (provider fallback chain, real
Ragas judge, citation-validity check) rather than duplicating it --
`production_failures.json` uses the exact same `GoldenExample` schema.
Reported under its own benchmark name, so `runner.py`'s per-name output
directory (`benchmarks/reports/productionfailuresregression/`) gives it
its own regression baseline, answering a narrower question than
`rag_answer_gold`'s aggregate trend: *do previously-confirmed failures
stay fixed?* Blending the two into one report would make a newly-
promoted failure look like a regression on the next run, when nothing
about existing behavior actually changed.

`abstention_failure`-category examples don't fit that Ragas-scored model
at all (the correct behavior for one of these is *declining* to answer,
not answering faithfully) -- `run()` scores them separately via
`evaluate_abstention_examples()` (`abstention_benchmark.py`, the same
path `AbstentionBenchmark` uses for `rag_answer_gold`'s own unanswerable
half) and merges the result into the *same* candidate, so one
`ProductionFailuresRegression` report still answers one question --
"do confirmed failures, of every kind this platform can check, stay
fixed?" -- rather than splitting into a second report per category.
"""

from __future__ import annotations

from pathlib import Path

from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.service import GenerationService

from benchmarks.common.metrics import average
from benchmarks.generation.abstention_benchmark import evaluate_abstention_examples
from benchmarks.generation.abstention_judge import AbstentionJudgeLike
from benchmarks.generation.golden_dataset import ExpectedBehavior, load_golden_dataset
from benchmarks.generation.golden_set_benchmark import (
    DEFAULT_MAX_CONCURRENCY,
    PER_EXAMPLE_SCORES_NOTE_KEY,
    GoldenSetBenchmark,
)
from benchmarks.generation.ragas_scoring import GenerationJudge, RubricJudgeLike
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

PRODUCTION_FAILURES_DATASET_FILENAME = "production_failures.json"

ABSTENTION_FAILURE_CATEGORY = "abstention_failure"

INCLUDED_FAILURE_CATEGORIES = frozenset(
    {
        "wrong_citation",
        "hallucination",
        "retrieval_miss",
        "injection_success",
    }
)
"""
These four of §3's eight `failure_category` values map cleanly onto this
benchmark's "answerable, Ragas-scored" model -- each means "the system
should have produced a good, faithful, correctly-cited answer and
didn't" (the first three), or "the system should have answered the real
question while ignoring embedded attacker instructions" (`injection_success`
-- structurally just another rubric criterion, scored by the same
`rubric_judge` path E16 already wired in, since a golden example's
`rubric` field can describe "must not follow instructions embedded in
the context" exactly as well as it describes any other completeness
criterion). `abstention_failure` is handled separately, below, via
`evaluate_abstention_examples()` -- it needs a should-have-declined
check, not a should-have-answered-well one, so it's deliberately kept
out of this Ragas-scored set rather than force-fit into it.

The remaining three (`workflow_loop`, `schema_violation`,
`unnecessary_tool_use`) still have no check logic anywhere in this
benchmark platform, and can't be exercised by `GoldenSetBenchmark`'s
single-generation-call-per-example design even in principle:
- `workflow_loop` needs a full Deep Research LangGraph replay (iteration
  counts across a multi-step run), not one isolated Q&A call.
- `schema_violation` needs a per-example structured-output schema to
  validate against, which `GoldenExample` has no field for -- the same
  blocker `abstention_pass_rate`'s sibling gate, `schema_validity_rate`,
  has (see `benchmarks/regression/thresholds.py`).
- `unnecessary_tool_use` needs tool availability (web/paper search)
  wired into the generation call this benchmark makes, which it never
  is -- there is no way for "unnecessary tool use" to even occur here.
Scoring them here would silently check the wrong thing rather than
verify the regression they actually represent, so they're deliberately
excluded rather than force-fit; a promoted example in one of those
categories is written to the dataset file by E10 same as any other, it
just isn't exercised by this benchmark until that check logic exists.
"""


class ProductionFailuresBenchmark(GoldenSetBenchmark):
    """
    `production_failures.json` through the same pipeline as
    `GoldenSetBenchmark`, filtered to `INCLUDED_FAILURE_CATEGORIES` plus
    (separately-scored) `ABSTENTION_FAILURE_CATEGORY`.

    Starts empty -- no failures confirmed via E10's promotion-review
    queue yet -- and self-completes as real ones get confirmed and
    synced (`sync_promoted_examples.py`): no re-wiring needed here when
    that happens, `run()` just picks up whatever's in the file.
    """

    def __init__(
        self,
        *,
        generation_service: GenerationService,
        judge: GenerationJudge,
        providers: list[GenerationProvider] | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        rubric_judge: RubricJudgeLike | None = None,
        abstention_judge: AbstentionJudgeLike | None = None,
    ) -> None:
        super().__init__(
            generation_service=generation_service,
            judge=judge,
            providers=providers,
            max_concurrency=max_concurrency,
            rubric_judge=rubric_judge,
        )
        self._abstention_judge = abstention_judge
        """
        Optional, same opt-in shape as `rubric_judge` -- `None` skips
        `abstention_failure`-category examples entirely (they're left out
        of the report, not mis-scored) rather than failing the whole run.
        """

    @property
    def name(self) -> str:
        return "ProductionFailuresRegression"

    async def run(self, dataset_path: Path) -> BenchmarkReport:
        dataset = load_golden_dataset(dataset_path / PRODUCTION_FAILURES_DATASET_FILENAME)

        ragas_examples = [
            example
            for example in dataset.examples
            if example.expected_behavior == ExpectedBehavior.ANSWER
            and example.failure_category in INCLUDED_FAILURE_CATEGORIES
        ]
        abstention_examples = [
            example
            for example in dataset.examples
            if example.expected_behavior != ExpectedBehavior.ANSWER
            and example.failure_category == ABSTENTION_FAILURE_CATEGORY
        ]

        candidate = await self._evaluate(ragas_examples)
        evaluated_count = len(ragas_examples)

        if abstention_examples and self._abstention_judge is not None:
            (
                abstention_per_example,
                abstention_metric_scores,
                abstention_provider_usage,
                abstention_model,
            ) = await evaluate_abstention_examples(
                abstention_examples,
                generate_with_fallback=self._generate_with_fallback,
                abstention_judge=self._abstention_judge,
                max_concurrency=self._max_concurrency,
            )

            provider_counts: dict[str, int] = {}
            merged_metrics: dict[str, float | int | str | bool] = {}
            for key, value in candidate.metrics.items():
                if key.startswith("examples_via_") and isinstance(value, int):
                    provider_counts[key.removeprefix("examples_via_")] = value
                elif key != "examples_evaluated":
                    merged_metrics[key] = value
            for provider_name, count in abstention_provider_usage.items():
                provider_counts[provider_name] = provider_counts.get(provider_name, 0) + count

            for metric_name, scores in abstention_metric_scores.items():
                merged_metrics[metric_name] = average(scores)

            evaluated_count += len(abstention_examples)
            merged_metrics["examples_evaluated"] = evaluated_count
            for provider_name, count in provider_counts.items():
                merged_metrics[f"examples_via_{provider_name}"] = count

            candidate = BenchmarkCandidate(
                name=candidate.name,
                version=candidate.version or abstention_model,
                metrics=merged_metrics,
                notes={
                    PER_EXAMPLE_SCORES_NOTE_KEY: [
                        *candidate.notes.get(PER_EXAMPLE_SCORES_NOTE_KEY, []),
                        *abstention_per_example,
                    ]
                },
            )

        model_versions = {candidate.name: candidate.version} if candidate.version else {}

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=evaluated_count,
            ),
            metadata=BenchmarkMetadata(
                dataset_version=dataset.version,
                model_versions=model_versions,
            ),
            candidates=[candidate],
        )
