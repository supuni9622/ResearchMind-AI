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
"""

from __future__ import annotations

from pathlib import Path

from benchmarks.generation.golden_dataset import ExpectedBehavior, load_golden_dataset
from benchmarks.generation.golden_set_benchmark import GoldenSetBenchmark
from benchmarks.models.report import BenchmarkDataset, BenchmarkMetadata, BenchmarkReport

PRODUCTION_FAILURES_DATASET_FILENAME = "production_failures.json"

INCLUDED_FAILURE_CATEGORIES = frozenset(
    {
        "wrong_citation",
        "hallucination",
        "retrieval_miss",
    }
)
"""
Only these three of §3's eight `failure_category` values map cleanly onto
this benchmark's "answerable, Ragas-scored" model -- each means "the
system should have produced a good, faithful, correctly-cited answer and
didn't," exactly what `score_generation()` and the citation-validity
check already verify. The other five (`abstention_failure`,
`workflow_loop`, `schema_violation`, `injection_success`,
`unnecessary_tool_use`) need a different kind of check -- did it abstain,
did it stay within N iterations, did the schema validate, did it refuse
the injection, did it skip the unneeded tool call -- that doesn't exist
yet. Scoring them here would silently check the wrong thing rather than
verify the regression they actually represent, so they're deliberately
excluded rather than force-fit; a promoted example in one of those
categories is written to the dataset file by E10 same as any other, it
just isn't exercised by this benchmark until that check logic exists.
"""


class ProductionFailuresBenchmark(GoldenSetBenchmark):
    """
    `production_failures.json` through the same pipeline as
    `GoldenSetBenchmark`, filtered to `INCLUDED_FAILURE_CATEGORIES`.

    Starts empty -- no failures confirmed via E10's promotion-review
    queue yet -- and self-completes as real ones get confirmed and
    synced (`sync_promoted_examples.py`): no re-wiring needed here when
    that happens, `run()` just picks up whatever's in the file.
    """

    @property
    def name(self) -> str:
        return "ProductionFailuresRegression"

    async def run(self, dataset_path: Path) -> BenchmarkReport:
        dataset = load_golden_dataset(dataset_path / PRODUCTION_FAILURES_DATASET_FILENAME)

        included = [
            example
            for example in dataset.examples
            if example.expected_behavior == ExpectedBehavior.ANSWER
            and example.failure_category in INCLUDED_FAILURE_CATEGORIES
        ]

        candidate = await self._evaluate(included)

        model_versions = {candidate.name: candidate.version} if candidate.version else {}

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(included),
            ),
            metadata=BenchmarkMetadata(
                dataset_version=dataset.version,
                model_versions=model_versions,
            ),
            candidates=[candidate],
        )
