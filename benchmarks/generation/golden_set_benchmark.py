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
plus up to 4 real Ragas judge calls per example. Intended for the
release-candidate tier only.

Runs against an ordered provider fallback chain, not every registered
provider -- a real Groq run hit a daily-token-limit 429
(`tokens per day (TPD): Limit 100000`) partway through a 115-example
pass, which would have poisoned that whole candidate. One release-
candidate score from a resilient chain (default: OpenAI, falling back to
Claude per-example on failure) is what this benchmark actually needs;
cross-provider comparison is `GenerationBenchmark`'s job, not this one's.

Examples run concurrently, bounded by `max_concurrency` (default 5, see
`DEFAULT_MAX_CONCURRENCY`) -- standard practice for bulk I/O-bound LLM
evaluation, and independent of the fallback-chain fix above (concurrency
doesn't change total token consumption, so it wouldn't have prevented
that specific daily-limit 429 on its own; it's purely a throughput
improvement on top of it).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import uuid4

from app.ai.knowledge.context.citations.service import CitationService
from app.ai.knowledge.context.citations.validity import (
    check_prompt_context_citation_validity,
)
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.service import GenerationService

from benchmarks.common.metrics import average
from benchmarks.generation.golden_dataset import (
    ExpectedBehavior,
    GoldenExample,
    Workflow,
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

DEFAULT_PROVIDER_FALLBACK_CHAIN = [GenerationProvider.OPENAI, GenerationProvider.CLAUDE]

CITATION_SYSTEM_PROMPT = (
    "Answer the user's question using only the supplied evidence. Reference "
    "supporting evidence using its citation ID in brackets, e.g. [S1]. Do "
    "not invent citation IDs."
)
"""
E20's citation-metric wiring (EVALUATION_IMPLEMENTATION_TRACKER.md): reuses
the citation-integrity clause of `ResearchSynthesisService`'s real
production instruction (`research/synthesis/service.py`) verbatim --
"do not invent citation IDs" -- rather than inventing new wording.

Applied to `linear_research`/`deep_research`-workflow examples only, per
`_evaluate_one_example`'s `expects_citations` check -- **not** `chat`,
which is intentionally citation-free in production (direct instruction,
2026-08-12), so instructing it here would test a scenario that can never
occur in real Chat traffic. Neither Chat's nor Linear Research's real
call sites (`api/v1/chat.py`, `ai/research/service.py`) set this
instruction today -- only Deep Research's synthesis step does -- so
Linear Research examples still don't mirror production *exactly*, but
unlike Chat, Linear Research citations are a real, intended product
behavior (it already builds real `Citation` objects and labels sources),
just not yet backed by an explicit model instruction -- a separate,
already-flagged product gap, not something this benchmark should also
leave untested.
"""

DEFAULT_MAX_CONCURRENCY = 5
"""
Examples evaluated concurrently, bounded by an `asyncio.Semaphore` --
115 examples fully sequential (the original design) meant ~10-15s per
example (one generation call plus up to 4 real Ragas judge calls) times
115, tens of minutes for one run. Bounded concurrency is standard
practice for this kind of I/O-bound bulk LLM evaluation and doesn't
change *total* token consumption (so it wouldn't have prevented the
Groq daily-token-limit 429 the fallback chain above exists for -- that's
a total-usage limit, not a pacing one) -- this is purely a throughput
improvement, independent of that fix. Conservative default: high enough
to matter, low enough not to trip a provider's requests-per-minute
limit the way an unbounded `asyncio.gather` over all 115 at once could.
"""

PER_EXAMPLE_SCORES_NOTE_KEY = "per_example_scores"
"""
`BenchmarkCandidate.notes[...]` key holding this run's per-example detail
-- a list of `{"example_id", "metric", "score", "passed", "reason"[,
"provider"]}` dicts (`provider` records which link in the fallback chain
actually served that example, present only on real metric checks, not
`"error"` placeholders). `BenchmarkReport`/`BenchmarkCandidate` are
shared across every benchmark and deliberately stay aggregate-only (see
their own module docstring); `notes: dict[str, Any]` is the existing,
already-generic escape hatch other benchmarks use for extra per-run
detail (e.g. `GenerationBenchmark`'s `error` note), not a new mechanism
invented here. `persist_golden_set_scores.py` is the only reader of this
key.
"""


class GoldenSetBenchmark(Benchmark):
    """
    Runs `rag_answer_gold`'s answerable examples through a live
    generation call -- retried down an ordered provider fallback chain
    per example on failure -- then scores each with the real Ragas judge
    suite. Produces exactly one `BenchmarkCandidate` representing that
    chain, not one per provider.
    """

    def __init__(
        self,
        *,
        generation_service: GenerationService,
        judge: GenerationJudge,
        providers: list[GenerationProvider] | None = None,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        citation_service: CitationService | None = None,
    ) -> None:
        self._generation_service = generation_service
        self._judge = judge
        self._providers = (
            providers if providers is not None else list(DEFAULT_PROVIDER_FALLBACK_CHAIN)
        )
        self._max_concurrency = max_concurrency
        self._citation_service = (
            citation_service if citation_service is not None else CitationService()
        )

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

        candidate = await self._evaluate(answerable)

        model_versions = {candidate.name: candidate.version} if candidate.version else {}

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
            candidates=[candidate],
        )

    async def _generate_with_fallback(
        self,
        request: GenerationRequest,
    ) -> tuple[GenerationProvider, str, str] | list[str]:
        """
        Try each provider in `self._providers` in order; returns
        `(provider, model, content)` for the first one that succeeds, or
        the list of `"{provider}: {error}"` strings (one per provider
        tried) if every provider in the chain failed for this example --
        kept, not discarded, so the resulting per-example `reason` says
        *why* each link failed rather than just that the chain gave up.
        A provider failing here (rate limit, outage, ...) does not retry
        that same provider -- `GenerationService.generate()` already
        retries transient errors internally; this only moves on to the
        *next* provider once that's exhausted.
        """

        errors: list[str] = []
        for provider in self._providers:
            try:
                result = await self._generation_service.generate(
                    request=request,
                    provider=provider,
                )
                return provider, result.model, result.content
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider.value}: {exc}")

        return errors

    async def _evaluate(
        self,
        examples: list[GoldenExample],
    ) -> BenchmarkCandidate:
        """
        Run every answerable golden example through the provider
        fallback chain, score each with the real Ragas judge, and
        aggregate into one candidate.

        Examples run concurrently, bounded by `self._max_concurrency`
        (`asyncio.Semaphore`) -- safe to parallelize across *examples*
        because each is fully independent (its own request, own
        fallback attempt, own judge call); only the fallback attempts
        *within* one example stay a strict sequential loop
        (`_generate_with_fallback`), since trying Claude before OpenAI's
        result is known would defeat the point of a fallback. A single
        example's failure (every provider in the chain failed, or judge
        error) is recorded in that example's own per-example entry
        rather than aborting the run -- a golden-set pass has ~100x more
        individual calls than a candidate-level try/except would
        tolerate losing the whole run to.
        """

        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def _bounded(
            example: GoldenExample,
        ) -> tuple[list[dict[str, object]], GenerationProvider | None, str | None]:
            async with semaphore:
                return await self._evaluate_one_example(example)

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

        metrics: dict[str, float | int | str | bool] = {
            "examples_evaluated": len(examples),
            **{metric_name: average(scores) for metric_name, scores in metric_scores.items()},
        }
        for provider_name, count in provider_usage.items():
            metrics[f"examples_via_{provider_name}"] = count

        return BenchmarkCandidate(
            name="+".join(provider.value for provider in self._providers),
            version=model,
            metrics=metrics,
            notes={PER_EXAMPLE_SCORES_NOTE_KEY: per_example},
        )

    async def _evaluate_one_example(
        self,
        example: GoldenExample,
    ) -> tuple[list[dict[str, object]], GenerationProvider | None, str | None]:
        """Returns `(per-example notes entries, provider used, model used)`
        -- `provider`/`model` are `None` when every provider in the
        fallback chain failed for this example (nothing was generated to
        attribute either to)."""

        source_filename = (
            example.reference_context_ids[0] if example.reference_context_ids else "benchmark"
        )
        tagged_context = "\n\n".join(example.contexts)

        chunks = [
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
        ]
        # E20's citation-metric wiring: real Citation objects (S1, S2, ...),
        # same CitationService production uses, so the citation-validity
        # check below has real known_citation_ids to work against -- not
        # just the chunks themselves.
        citation_result = await self._citation_service.build(chunks)
        prompt_context = PromptContext(
            context=tagged_context,
            chunks=chunks,
            citations=citation_result.citations,
        )

        # Chat is intentionally citation-free in production (direct
        # instruction, 2026-08-12) -- Linear Research/Deep Research both
        # cite. Instructing chat-workflow examples to cite here would test
        # a scenario that cannot occur in real Chat traffic, the same
        # "measures something that can't happen" problem the rest of this
        # gate exists to avoid.
        expects_citations = example.workflow != Workflow.CHAT

        request = GenerationRequest(
            prompt_context=prompt_context,
            system_prompt=CITATION_SYSTEM_PROMPT if expects_citations else None,
            user_prompt=example.question,
        )

        outcome = await self._generate_with_fallback(request)
        if isinstance(outcome, list):
            return (
                [
                    {
                        "example_id": example.example_id,
                        "metric": "error",
                        "score": None,
                        "passed": False,
                        "reason": "every provider in the fallback chain failed: "
                        + "; ".join(outcome),
                    }
                ],
                None,
                None,
            )

        used_provider, model, content = outcome

        try:
            report = await score_generation(
                question=example.question,
                answer=content,
                contexts=example.contexts,
                reference=example.reference_answer,
                judge=self._judge,
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
                "metric": check.metric,
                "score": check.score,
                "passed": check.passed,
                "reason": check.reason,
                "provider": used_provider.value,
            }
            for check in report.checks
        ]

        # E20's citation-metric wiring (EVALUATION_IMPLEMENTATION_TRACKER.md):
        # this is what actually populates thresholds.py's
        # `fabricated_citation_rate` absolute gate, previously declared but
        # never emitted by any benchmark run. Deterministic, no LLM call --
        # unlike `score_generation` above, not wrapped in its own
        # try/except: a failure here is a real bug (malformed citations
        # payload), not an external-service error worth degrading past.
        # Skipped for chat-workflow examples (see `expects_citations`
        # above) -- nothing instructed the model to cite, so checking
        # would only ever trivially pass, not measure anything real.
        if expects_citations:
            citation_report = check_prompt_context_citation_validity(
                content=content,
                prompt_context=prompt_context,
            )
            entries.append(
                {
                    "example_id": example.example_id,
                    "metric": "fabricated_citation_rate",
                    "score": citation_report.fabricated_citation_rate,
                    "passed": citation_report.valid,
                    "reason": "; ".join(check.reason for check in citation_report.checks),
                    "provider": used_provider.value,
                }
            )

        return entries, used_provider, model
