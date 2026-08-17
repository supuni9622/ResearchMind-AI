"""Paired memory-on/off answer utility evaluation for M6."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Protocol

from app.core.settings import settings
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from benchmarks.common.report_generator import BenchmarkReportGenerator
from benchmarks.memory.dataset import MemoryEvaluationDataset, load_memory_evaluation_dataset
from benchmarks.memory.metrics import average
from benchmarks.models.report import (
    BenchmarkCandidate,
    BenchmarkDataset,
    BenchmarkMetadata,
    BenchmarkReport,
)

DEFAULT_MEMORY_UTILITY_JUDGE_MODEL = "gpt-4o-mini"


class MemoryAnswerPair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    answer_without_memory: str
    answer_with_memory: str


class MemoryAnswerPairs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: str
    version: str
    dataset_version: str
    pairs: list[MemoryAnswerPair]


class MemoryUtilityJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1)
    correctness_without: float = Field(ge=0, le=1)
    correctness_with: float = Field(ge=0, le=1)
    personalization_without: float = Field(ge=0, le=1)
    personalization_with: float = Field(ge=0, le=1)
    evidence_quality_without: float = Field(ge=0, le=1)
    evidence_quality_with: float = Field(ge=0, le=1)
    irrelevant_memory_harm: float = Field(ge=0, le=1)


class MemoryUtilityJudge(Protocol):
    async def evaluate(
        self,
        *,
        question: str,
        reference_answer: str | None,
        rubric: str | None,
        answer_without_memory: str,
        answer_with_memory: str,
    ) -> MemoryUtilityJudgment: ...


class OpenAIMemoryUtilityJudge:
    def __init__(
        self, *, client: AsyncOpenAI, model: str = DEFAULT_MEMORY_UTILITY_JUDGE_MODEL
    ) -> None:
        self._client = client
        self._model = model

    async def evaluate(
        self,
        *,
        question: str,
        reference_answer: str | None,
        rubric: str | None,
        answer_without_memory: str,
        answer_with_memory: str,
    ) -> MemoryUtilityJudgment:
        completion = await self._client.chat.completions.parse(
            model=self._model,
            temperature=0,
            max_completion_tokens=500,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Compare two answers to the same request. Score task correctness, "
                        "personalization adherence, and evidence quality from 0 to 1. "
                        "Score irrelevant-memory harm from 0 (none) to 1 (severe). Do not "
                        "reward an answer merely for mentioning personal details. Explain "
                        "the comparison briefly before returning scores."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question: {question}\n\nReference: {reference_answer or 'none'}\n\n"
                        f"Rubric: {rubric or 'none'}\n\nWithout memory:\n{answer_without_memory}"
                        f"\n\nWith memory:\n{answer_with_memory}"
                    ),
                },
            ],
            response_format=MemoryUtilityJudgment,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Memory utility judge returned no schema-valid result")
        return parsed


async def score_answer_pairs(
    *,
    dataset: MemoryEvaluationDataset,
    pairs: MemoryAnswerPairs,
    judge: MemoryUtilityJudge,
) -> BenchmarkReport:
    if pairs.dataset_version != dataset.version:
        raise ValueError("Answer-pair dataset_version does not match ground truth")
    query_by_id = {query.query_id: query for query in dataset.queries}
    pair_by_id = {pair.query_id: pair for pair in pairs.pairs}
    if set(query_by_id) != set(pair_by_id) or len(pair_by_id) != len(pairs.pairs):
        raise ValueError("Answer-pair query IDs must match dataset exactly")

    utility_scores: list[float] = []
    harm_scores: list[float] = []
    per_query: dict[str, dict[str, float | str]] = {}
    for query_id, query in query_by_id.items():
        pair = pair_by_id[query_id]
        judgment = await judge.evaluate(
            question=query.query,
            reference_answer=query.reference_answer,
            rubric=query.answer_rubric,
            answer_without_memory=pair.answer_without_memory,
            answer_with_memory=pair.answer_with_memory,
        )
        utility = average(
            [
                judgment.correctness_with - judgment.correctness_without,
                judgment.personalization_with - judgment.personalization_without,
                judgment.evidence_quality_with - judgment.evidence_quality_without,
            ]
        )
        utility_scores.append(utility)
        harm_scores.append(judgment.irrelevant_memory_harm)
        per_query[query_id] = {
            "memory_utility": round(utility, 6),
            "irrelevant_memory_harm": judgment.irrelevant_memory_harm,
            "reason": judgment.reason,
        }

    metrics: dict[str, float | int | str | bool] = {
        "memory_utility": round(average(utility_scores), 6),
        "irrelevant_memory_harm": round(average(harm_scores), 6),
        "query_count": len(dataset.queries),
    }
    return BenchmarkReport(
        benchmark_name="MemoryAnswerUtility",
        dataset=BenchmarkDataset(name=dataset.name, document_count=len(dataset.queries)),
        metadata=BenchmarkMetadata(
            dataset_version=dataset.version,
            model_versions={pairs.candidate: pairs.version},
        ),
        candidates=[
            BenchmarkCandidate(
                name=pairs.candidate,
                version=pairs.version,
                metrics=metrics,
                notes={"per_query": per_query},
            )
        ],
    )


async def _main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for paired memory utility evaluation")
    dataset = load_memory_evaluation_dataset(args.dataset)
    pairs = MemoryAnswerPairs.model_validate(json.loads(args.pairs.read_text(encoding="utf-8")))
    report = await score_answer_pairs(
        dataset=dataset,
        pairs=pairs,
        judge=OpenAIMemoryUtilityJudge(client=AsyncOpenAI(api_key=settings.openai_api_key)),
    )
    generator = BenchmarkReportGenerator()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(generator.generate_json(report), encoding="utf-8")
    (args.output / "report.md").write_text(generator.generate_markdown(report), encoding="utf-8")
    print(f"Memory answer utility report written to {args.output}")


if __name__ == "__main__":
    asyncio.run(_main())
