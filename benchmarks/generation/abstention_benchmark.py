"""
Abstention regression benchmark (`EVALUATION_PLAN.md` §13's third
absolute gate, `abstention_pass_rate` -- declared 2026-08-11, never
previously populated by any benchmark run; E20 flagged why: needed E1's
golden set, which existed, but also a dedicated non-Ragas scoring path
for the unanswerable half of that set, which didn't).

`GoldenSetBenchmark` deliberately only ever runs the *answerable* half
of `rag_answer_gold` (`expected_behavior == ANSWER`) -- Ragas's
faithfulness/context_precision/etc. aren't meaningful for a question the
system should decline. This is the flip side: runs the *unanswerable*
half through the same live generation + provider-fallback machinery
(`GoldenSetBenchmark._generate_with_fallback`, inherited unchanged), then
scores whether the response correctly abstained via `AbstentionJudge`
instead of the Ragas suite.

`score_abstention_example()`/`evaluate_abstention_examples()` are
exported (not private to `AbstentionBenchmark`) because
`ProductionFailuresBenchmark` needs the identical scoring path for its
own `abstention_failure`-category examples, alongside its existing
Ragas-scored categories in the *same* report -- see that module's own
docstring for why those live in one merged candidate rather than a
second `AbstentionBenchmark` run.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.service import GenerationService

from benchmarks.generation.abstention_judge import AbstentionJudgeLike
from benchmarks.generation.golden_dataset import (
    ExpectedBehavior,
    GoldenExample,
    load_golden_dataset,
)
from benchmarks.generation.golden_set_benchmark import (
    DEFAULT_MAX_CONCURRENCY,
    DEFAULT_PROVIDER_FALLBACK_CHAIN,
    GOLDEN_DATASET_FILENAME,
    GoldenSetBenchmark,
)
from benchmarks.models.report import BenchmarkDataset, BenchmarkMetadata, BenchmarkReport

GenerateWithFallback = Callable[
    [GenerationRequest], Awaitable[tuple[GenerationProvider, str, str] | list[str]]
]


async def score_abstention_example(
    example: GoldenExample,
    *,
    generate_with_fallback: GenerateWithFallback,
    abstention_judge: AbstentionJudgeLike,
) -> tuple[list[dict[str, object]], GenerationProvider | None, str | None]:
    """Returns `(per-example notes entries, provider used, model used)`,
    same shape as `GoldenSetBenchmark._evaluate_one_example`."""

    # No retrieved context: the golden set's unanswerable examples
    # deliberately carry none (see test_faithfulness.py's own contract
    # test) -- the correct behavior is recognizing there's nothing to
    # work with, not evaluating provided-but-insufficient evidence.
    request = GenerationRequest(
        prompt_context=PromptContext(context="", chunks=[]),
        user_prompt=example.question,
    )

    outcome = await generate_with_fallback(request)
    if isinstance(outcome, list):
        return (
            [
                {
                    "example_id": example.example_id,
                    "metric": "error",
                    "score": None,
                    "passed": False,
                    "reason": "every provider in the fallback chain failed: " + "; ".join(outcome),
                }
            ],
            None,
            None,
        )

    used_provider, model, content = outcome

    try:
        result = await abstention_judge.ascore(
            question=example.question,
            answer=content,
            rubric=example.rubric,
        )
    except Exception as exc:  # noqa: BLE001
        return (
            [
                {
                    "example_id": example.example_id,
                    "metric": "error",
                    "score": None,
                    "passed": False,
                    "reason": f"scoring failed: {exc}",
                }
            ],
            used_provider,
            model,
        )

    entries: list[dict[str, object]] = [
        {
            "example_id": example.example_id,
            "metric": "abstention_pass_rate",
            "score": 1.0 if result.passed else 0.0,
            "passed": result.passed,
            "reason": result.reason,
            "provider": used_provider.value,
        }
    ]

    return entries, used_provider, model


async def evaluate_abstention_examples(
    examples: list[GoldenExample],
    *,
    generate_with_fallback: GenerateWithFallback,
    abstention_judge: AbstentionJudgeLike,
    max_concurrency: int,
) -> tuple[list[dict[str, object]], dict[str, list[float]], dict[str, int], str | None]:
    """
    Bounded-concurrency `score_abstention_example()` over `examples`,
    returning the raw `(per_example, metric_scores, provider_usage,
    model)` pieces -- the same aggregation shape
    `GoldenSetBenchmark._evaluate()` builds internally, exposed here (not
    a `BenchmarkCandidate` directly) so `ProductionFailuresBenchmark` can
    merge it with its own Ragas-scored candidate into one combined
    candidate rather than two separate ones.
    """

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(
        example: GoldenExample,
    ) -> tuple[list[dict[str, object]], GenerationProvider | None, str | None]:
        async with semaphore:
            return await score_abstention_example(
                example,
                generate_with_fallback=generate_with_fallback,
                abstention_judge=abstention_judge,
            )

    results = await asyncio.gather(*(_bounded(example) for example in examples))

    per_example: list[dict[str, object]] = []
    metric_scores: dict[str, list[float]] = {}
    provider_usage: dict[str, int] = {}
    model: str | None = None

    for entries, used_provider, result_model in results:
        per_example.extend(entries)
        if result_model is not None:
            model = result_model
        if used_provider is not None:
            provider_usage[used_provider.value] = provider_usage.get(used_provider.value, 0) + 1
        for entry in entries:
            score = entry["score"]
            if entry["metric"] != "error" and isinstance(score, int | float):
                metric_scores.setdefault(str(entry["metric"]), []).append(float(score))

    return per_example, metric_scores, provider_usage, model


class AbstentionBenchmark(GoldenSetBenchmark):
    """
    Overrides `__init__` (an abstention judge, not a Ragas judge -- no
    `rubric_judge`/`citation_service` needed, citations aren't relevant
    to a response that should decline) and `run()`/`_evaluate_one_example()`
    (different filter, different scoring). `_generate_with_fallback()` is
    inherited unchanged from `GoldenSetBenchmark`.
    """

    def __init__(
        self,
        *,
        generation_service: GenerationService,
        abstention_judge: AbstentionJudgeLike,
        providers: list[GenerationProvider] | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._generation_service = generation_service
        self._abstention_judge = abstention_judge
        self._providers = (
            providers if providers is not None else list(DEFAULT_PROVIDER_FALLBACK_CHAIN)
        )
        self._max_concurrency = max_concurrency

    @property
    def name(self) -> str:
        return "AbstentionRegression"

    async def run(self, dataset_path: Path) -> BenchmarkReport:
        dataset = load_golden_dataset(dataset_path / GOLDEN_DATASET_FILENAME)

        unanswerable = [
            example
            for example in dataset.examples
            if example.expected_behavior != ExpectedBehavior.ANSWER
        ]

        candidate = await self._evaluate(unanswerable)

        model_versions = {candidate.name: candidate.version} if candidate.version else {}

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(unanswerable),
            ),
            metadata=BenchmarkMetadata(
                dataset_version=dataset.version,
                model_versions=model_versions,
            ),
            candidates=[candidate],
        )

    async def _evaluate_one_example(
        self,
        example: GoldenExample,
    ) -> tuple[list[dict[str, object]], GenerationProvider | None, str | None]:
        return await score_abstention_example(
            example,
            generate_with_fallback=self._generate_with_fallback,
            abstention_judge=self._abstention_judge,
        )


__all__ = [
    "AbstentionBenchmark",
    "evaluate_abstention_examples",
    "score_abstention_example",
]
