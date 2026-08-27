"""M6 captured-run benchmark producing the canonical benchmark report."""

from __future__ import annotations

from benchmarks.memory.dataset import MemoryEvaluationDataset
from benchmarks.memory.metrics import (
    average,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    selection_rate,
)
from benchmarks.memory.results import MemoryCandidateResults
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

TOP_K = 5


def score_memory_candidate(
    *, dataset: MemoryEvaluationDataset, captured: MemoryCandidateResults
) -> BenchmarkReport:
    if captured.dataset_version != dataset.version:
        raise ValueError(
            "Captured result dataset_version does not match ground truth: "
            f"{captured.dataset_version!r} != {dataset.version!r}"
        )

    query_by_id = {query.query_id: query for query in dataset.queries}
    results_by_id = {result.query_id: result for result in captured.results}
    missing = set(query_by_id) - set(results_by_id)
    extra = set(results_by_id) - set(query_by_id)
    if missing or extra or len(results_by_id) != len(captured.results):
        raise ValueError(
            f"Captured query IDs must match dataset exactly; missing={sorted(missing)}, "
            f"extra={sorted(extra)}"
        )

    recalls: list[float] = []
    precisions: list[float] = []
    reciprocal_ranks: list[float] = []
    ndcgs: list[float] = []
    irrelevant_rates: list[float] = []
    stale_rates: list[float] = []
    contradictory_rates: list[float] = []
    unsafe_rates: list[float] = []
    scope_leaks = 0
    observed_memory_count = 0
    latencies: list[float] = []
    token_counts: list[float] = []
    per_query: dict[str, dict[str, float | int | str]] = {}

    for query_id, query in query_by_id.items():
        result = results_by_id[query_id]
        relevant = set(query.relevant_memory_ids)
        allowed = set(query.allowed_memory_ids)
        selected = result.selected_memory_ids
        retrieved = result.retrieved_memory_ids
        observed = set(retrieved + selected)
        leak_count = len(observed - allowed)
        irrelevant = set(selected) - relevant

        recall = recall_at_k(retrieved, relevant, TOP_K)
        precision = precision_at_k(retrieved, relevant, TOP_K)
        mrr = reciprocal_rank(retrieved, relevant)
        ndcg = ndcg_at_k(retrieved, relevant, TOP_K)

        if relevant:
            recalls.append(recall)
            precisions.append(precision)
            reciprocal_ranks.append(mrr)
            ndcgs.append(ndcg)
        irrelevant_rates.append(selection_rate(selected, irrelevant))
        stale_rates.append(selection_rate(selected, set(query.stale_memory_ids)))
        contradictory_rates.append(selection_rate(selected, set(query.contradictory_memory_ids)))
        unsafe_rates.append(selection_rate(selected, set(query.unsafe_memory_ids)))
        scope_leaks += leak_count
        observed_memory_count += len(observed)
        latencies.append(result.latency_ms)
        token_counts.append(float(result.selected_tokens))
        per_query[query_id] = {
            "category": query.category,
            "recall_at_5": round(recall, 6),
            "precision_at_5": round(precision, 6),
            "mrr": round(mrr, 6),
            "scope_leak_count": leak_count,
        }

    metrics: dict[str, float | int | str | bool] = {
        "recall_at_5": round(average(recalls), 6),
        "precision_at_5": round(average(precisions), 6),
        "mrr": round(average(reciprocal_ranks), 6),
        "ndcg_at_5": round(average(ndcgs), 6),
        "irrelevant_injection_rate": round(average(irrelevant_rates), 6),
        "stale_injection_rate": round(average(stale_rates), 6),
        "contradictory_injection_rate": round(average(contradictory_rates), 6),
        "unsafe_memory_injection_rate": round(average(unsafe_rates), 6),
        "scope_leak_rate": round(scope_leaks / max(1, observed_memory_count), 6),
        "avg_latency_ms": round(average(latencies), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "avg_selected_tokens": round(average(token_counts), 3),
        "query_count": len(dataset.queries),
    }

    return BenchmarkReport(
        benchmark_name="MemoryRetrieval",
        dataset=BenchmarkDataset(name=dataset.name, document_count=len(dataset.queries)),
        metadata=BenchmarkMetadata(
            dataset_version=dataset.version,
            model_versions={captured.candidate: captured.version},
        ),
        candidates=[
            BenchmarkCandidate(
                name=captured.candidate,
                version=captured.version,
                metrics=metrics,
                notes={"per_query": per_query},
            )
        ],
        summary={
            "scope_gate": "scope_leak_rate must equal 0",
            "unsafe_gate": "unsafe_memory_injection_rate must equal 0",
        },
    )
