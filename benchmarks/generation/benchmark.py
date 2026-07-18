"""
Generation benchmark.

Benchmarks every configured GenerationProvider (Groq, OpenAI, Claude,
Gemini, Ollama -- whichever have credentials configured, see
`app/ai/runtime/generation/create.py::create_generation_registry`)
against a shared, hand-curated query set with pre-supplied grounding
context, and produces a canonical BenchmarkReport.

Context is supplied directly by the dataset (see
`benchmarks/generation/dataset.py`) rather than retrieved live, so this
benchmark isolates generation quality from retrieval quality -- the same
separation-of-concerns already used by the chunking and embedding
benchmarks.

Scoring is deterministic and provider-agnostic (see
`benchmarks/generation/metrics.py`); no LLM judge is used.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk, PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.models import GenerationRequest
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.service import GenerationService

from benchmarks.common.metrics import average, percentile
from benchmarks.generation.dataset import (
    GenerationBenchmarkQuery,
    load_generation_queries,
)
from benchmarks.generation.metrics import (
    citation_accuracy,
    completeness,
    faithfulness,
    groundedness,
    relevance,
)
from benchmarks.interfaces.benchmark import Benchmark
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

QUERY_DATASET_FILENAME = "generation_queries.json"

BENCHMARK_OWNER_ID = "benchmark"

_CITATION_INSTRUCTION = (
    "Answer using only the provided context. The context begins with a "
    "[Source: <filename>] tag naming the document it was drawn from. When "
    "you state a fact from the context, name that source filename inline."
)
"""
Two things have to be true for `citation_accuracy` (see
`benchmarks/generation/metrics.py`) to be anything other than a
structural 0.0: the model has to be told to cite a filename (this
instruction), AND the model has to actually be given the filename
somewhere in its input, via the `[Source: ...]` tag prefixed onto the
context in `_evaluate()` below. An earlier version of this benchmark had
the instruction but not the tag -- confirmed via a real run against
Groq/OpenAI/Claude where citation_accuracy was 0.0 for every candidate,
since none of them could name a filename they were never given.
"""


class GenerationBenchmark(Benchmark):
    """
    Engineering benchmark for the Generation Platform.
    """

    def __init__(
        self,
        *,
        registry: GenerationRegistry,
        generation_service: GenerationService,
    ) -> None:
        self._registry = registry
        self._generation_service = generation_service

    @property
    def name(self) -> str:
        return "Generation"

    async def run(
        self,
        dataset_path: Path,
    ) -> BenchmarkReport:
        """
        Execute the generation benchmark.

        Args:
            dataset_path:
                Root benchmark dataset directory. Must contain a
                generation_queries.json ground-truth file.

        Returns:
            Canonical benchmark report.
        """

        query_dataset = load_generation_queries(
            dataset_path / QUERY_DATASET_FILENAME,
        )

        candidates = [
            await self._evaluate(provider, query_dataset.queries)
            for provider in self._registry.providers
        ]

        model_versions = {
            candidate.name: candidate.version for candidate in candidates if candidate.version
        }

        return BenchmarkReport(
            benchmark_name=self.name,
            dataset=BenchmarkDataset(
                name=dataset_path.name,
                document_count=len(query_dataset.queries),
            ),
            metadata=BenchmarkMetadata(
                dataset_version=query_dataset.version,
                model_versions=model_versions,
            ),
            candidates=candidates,
        )

    async def _evaluate(
        self,
        provider: GenerationProvider,
        queries: list[GenerationBenchmarkQuery],
    ) -> BenchmarkCandidate:
        """
        Run every benchmark query through a candidate provider and
        aggregate faithfulness, groundedness, relevance, completeness,
        citation accuracy, latency, and cost.
        """

        faithfulness_scores: list[float] = []
        groundedness_scores: list[float] = []
        relevance_scores: list[float] = []
        completeness_scores: list[float] = []
        citation_scores: list[float] = []
        latencies_ms: list[float] = []
        costs_usd: list[float] = []
        model: str | None = None
        error: str | None = None

        try:
            for query in queries:
                source_filename = query.citations[0] if query.citations else "benchmark"
                tagged_context = f"[Source: {source_filename}]\n{query.context}"

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
                                content=tagged_context,
                                score=1.0,
                            )
                        ],
                    ),
                    system_prompt=_CITATION_INSTRUCTION,
                    user_prompt=query.query,
                )

                result = await self._generation_service.generate(
                    request=request,
                    provider=provider,
                )

                model = result.model

                cited_filenames = [
                    citation.filename
                    for citation in result.citations
                    if isinstance(citation, Citation)
                ]

                faithfulness_scores.append(
                    faithfulness(result.content, query.context),
                )
                groundedness_scores.append(
                    groundedness(result.content, query.context),
                )
                relevance_scores.append(
                    relevance(result.content, query.query),
                )
                completeness_scores.append(
                    completeness(result.content, query.expected_answer),
                )
                citation_scores.append(
                    citation_accuracy(
                        result.content,
                        cited_filenames,
                        query.citations,
                    ),
                )
                latencies_ms.append(result.statistics.latency_ms)
                costs_usd.append(result.statistics.estimated_cost_usd)
        except Exception as exc:  # noqa: BLE001
            # Generation candidates call external, rate-limited provider
            # APIs. One candidate failing should not prevent the report
            # from covering the others.
            error = str(exc)

        queries_evaluated = len(latencies_ms)

        avg_cost_usd = (
            round(
                sum(costs_usd) / len(costs_usd),
                6,
            )
            if costs_usd
            else 0.0
        )

        metrics: dict[str, float | int | str | bool] = {
            "queries_evaluated": queries_evaluated,
            "faithfulness": average(faithfulness_scores),
            "groundedness": average(groundedness_scores),
            "relevance": average(relevance_scores),
            "completeness": average(completeness_scores),
            "citation_accuracy": average(citation_scores),
            "hallucination_rate": round(1 - average(faithfulness_scores), 4),
            "avg_latency_ms": round(average(latencies_ms), 2),
            "p95_latency_ms": round(percentile(latencies_ms, 0.95), 2),
            "avg_cost_usd": avg_cost_usd,
            "cost_per_query": avg_cost_usd,
            "cost_per_1k_queries": round(avg_cost_usd * 1000, 4),
        }

        notes: dict[str, object] = {
            "queries_total": len(queries),
        }

        if error is not None:
            notes["error"] = error

        return BenchmarkCandidate(
            name=provider.value,
            version=model,
            metrics=metrics,
            notes=notes,
        )
