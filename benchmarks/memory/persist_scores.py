"""Persist M6 per-query retrieval metrics into the existing eval_scores table."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.db.session import SessionFactory
from app.repositories.eval_score import EvalScoreRepository
from pydantic import BaseModel, ConfigDict

from benchmarks.models.report import BenchmarkReport


class MemoryOfflineScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    metric: str
    score: float


def extract_memory_offline_scores(report: BenchmarkReport) -> list[MemoryOfflineScore]:
    scores: list[MemoryOfflineScore] = []
    for candidate in report.candidates:
        per_query = candidate.notes.get("per_query", {})
        if not isinstance(per_query, dict):
            continue
        for query_id, raw_metrics in per_query.items():
            if not isinstance(raw_metrics, dict):
                continue
            for metric in (
                "recall_at_5",
                "precision_at_5",
                "mrr",
                "scope_leak_count",
                "memory_utility",
                "irrelevant_memory_harm",
            ):
                value = raw_metrics.get(metric)
                if isinstance(value, (int, float)):
                    scores.append(
                        MemoryOfflineScore(
                            query_id=str(query_id),
                            metric=f"memory_{metric}",
                            score=float(value),
                        )
                    )
    return scores


async def persist_memory_scores(report: BenchmarkReport, *, repository: EvalScoreRepository) -> int:
    scores = extract_memory_offline_scores(report)
    for item in scores:
        passed = item.score == 0 if item.metric == "memory_scope_leak_count" else None
        await repository.record_offline_example(
            dataset_example_id=item.query_id,
            metric_name=item.metric,
            score=item.score,
            passed=passed,
            reason=f"M6 offline memory benchmark: {item.metric}={item.score:.6f}",
        )
    return len(scores)


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = BenchmarkReport.model_validate_json(args.report.read_text(encoding="utf-8"))
    async with SessionFactory() as session:
        count = await persist_memory_scores(report, repository=EvalScoreRepository(session))
        await session.commit()
    print(f"Persisted {count} M6 offline memory scores")


if __name__ == "__main__":
    asyncio.run(_main())
