# Evaluation Platform PRD

**Project:** ResearchMind AI
**Platform:** Evaluation Platform
**Milestone:** Phase 4.1
**Status:** Planned
**Version:** 1.0
**Last Updated:** 2026-07-18

---

# 1. Purpose

The Evaluation Platform provides measurable quality assessment for every AI capability inside ResearchMind.

This platform exists to answer one question:

> Did this change actually improve the system?

Most RAG applications stop at retrieval and generation.

ResearchMind aims to become an **Evaluation Driven AI System**, where every AI improvement is measurable, benchmarked, reproducible, and regression-tested.

The Evaluation Platform becomes the quality layer sitting between AI Runtime and future Agent systems.

---

# 2. Motivation

Without evaluation:

- Improvements are subjective.
- Prompt changes are risky.
- Model upgrades are blind.
- Agent behavior cannot be measured.
- Refactoring can silently degrade quality.

Evaluation transforms ResearchMind from:

```text
AI Application
```

into:

```text
AI Engineering Platform
```

---

# 3. Platform Vision

```text
Knowledge Platform
        ↓
Generation Platform
        ↓
Observability Platform
        ↓
Evaluation Platform
        ↓
Research Runtime
        ↓
Agent Runtime
```

Evaluation must be completed before large-scale agent systems.

Agents without evaluation become demos rather than production systems.

---

# 4. Goals

---

## Goal 1

Create reproducible evaluation datasets.

---

## Goal 2

Measure AI quality objectively.

---

## Goal 3

Support experimentation.

---

## Goal 4

Detect regressions automatically.

---

## Goal 5

Enable CI quality gates.

---

# 5. Non Goals

This platform does NOT:

- Perform generation
- Execute research workflows
- Replace LangSmith datasets
- Replace observability
- Replace validation platform

Evaluation measures systems.

It does not execute them.

---

# 6. Responsibilities

The Evaluation Platform owns:

---

## Canonical Models

- EvaluationRequest
- EvaluationResult
- BenchmarkResult
- ExperimentResult
- RegressionResult

---

## Dataset Management

- Retrieval datasets
- Generation datasets
- Research datasets

---

## Benchmark Execution

- Retrieval benchmarks
- Generation benchmarks
- Research benchmarks

---

## Regression Detection

- Previous vs current comparisons
- Threshold policies
- CI failures

---

## Reports

- Markdown
- JSON
- Artifacts

---

# 7. LangSmith Responsibilities

LangSmith owns:

- Datasets
- Experiments
- Comparisons
- Traces

ResearchMind owns orchestration around LangSmith.

---

# 8. Architecture Principles

---

## Platform Owned Architecture

Evaluation logic belongs to ResearchMind.

External tools remain implementation details.

---

## Evaluation Driven Development

Every AI improvement must be measurable.

---

## Reproducibility

Benchmarks should produce identical results.

---

## Canonical Models

No provider-specific logic leaks outside adapters.

---

## Production First

Evaluation must eventually run in CI.

---

# 9. Architecture

```text
evaluation/

        datasets/
        evaluators/
        benchmarks/
        experiments/
        regression/
        reports/
        artifacts/
        langsmith/
```

---

# 10. Proposed Folder Structure

```text
app/ai/evaluation/

    models.py
    enums.py
    interfaces.py
    exceptions.py
    registry.py
    service.py
    create.py

    datasets/

        retrieval/
        generation/
        research/

    evaluators/

        retrieval/
        generation/
        research/

    benchmarks/

        retrieval/
        generation/
        research/

    experiments/

    regression/

    reports/

    artifacts/

    langsmith/
```

---

# 11. Canonical Models

---

# 11.1 EvaluationRequest

```python
class EvaluationRequest(BaseModel):
    dataset_name: str
    benchmark_type: BenchmarkType
    configuration: dict[str, Any]
```

---

# 11.2 EvaluationResult

```python
class EvaluationResult(BaseModel):
    execution_id: UUID
    benchmark_type: BenchmarkType
    score: float
    metrics: dict[str, float]
    duration_ms: float
```

---

# 11.3 BenchmarkResult

```python
class BenchmarkResult(BaseModel):
    benchmark_name: str
    metrics: dict[str, float]
    statistics: dict[str, Any]
```

---

# 11.4 ExperimentResult

```python
class ExperimentResult(BaseModel):
    experiment_name: str
    candidates: list[BenchmarkResult]
    winner: str | None
```

---

# 11.5 RegressionResult

```python
class RegressionResult(BaseModel):
    passed: bool
    regressions: list[RegressionIssue]
```

---

# 12. Enums

---

## BenchmarkType

```python
class BenchmarkType(str, Enum):
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    RESEARCH = "research"
```

---

## EvaluationStatus

```python
PENDING
RUNNING
COMPLETED
FAILED
```

---

# 13. Dataset Platform

---

# Purpose

Provide reproducible datasets.

---

# Structure

```text
datasets/

    retrieval/
    generation/
    research/
```

---

# Retrieval Dataset

```json
{
  "id": "1",
  "query": "...",
  "relevant_documents": [
      "doc_1",
      "doc_2"
  ]
}
```

---

# Generation Dataset

```json
{
  "query": "...",
  "context": "...",
  "expected_answer": "...",
  "citations": []
}
```

---

# Research Dataset

```json
{
  "query": "...",
  "expected_sections": [],
  "expected_sources": [],
  "expected_answer": ""
}
```

---

# Dataset Models

```python
RetrievalDatasetEntry
GenerationDatasetEntry
ResearchDatasetEntry
```

---

# Future

LangSmith dataset synchronization.

---

# 14. Retrieval Evaluation

---

# Goal

Measure retrieval quality.

---

# Metrics

---

## Recall@K

```text
Retrieved Relevant

/

Total Relevant
```

---

## Precision@K

```text
Relevant Retrieved

/

Retrieved
```

---

## MRR

Mean Reciprocal Rank.

---

## NDCG

Ranking quality.

---

## Latency

P50/P95/P99.

---

## Cost

Embedding + reranking cost.

---

## Coverage

Percentage of queries with at least one relevant result.

---

# Folder

```text
evaluators/retrieval/

    recall.py
    precision.py
    mrr.py
    ndcg.py
    latency.py
    cost.py
    coverage.py
```

---

# Benchmark Runner

```python
RetrievalBenchmarkRunner
```

---

# Output

```python
BenchmarkResult
```

---

# 15. Generation Evaluation

---

# Goal

Measure answer quality.

---

# Metrics

---

## Faithfulness

Are claims supported by context?

---

## Groundedness

Did the answer originate from retrieved evidence?

---

## Citation Accuracy

Are citations valid?

---

## Relevance

Did we answer the question?

---

## Completeness

Did we miss important information?

---

## Hallucination Rate

Unsupported claims.

---

# Folder

```text
evaluators/generation/

    faithfulness.py
    groundedness.py
    citations.py
    relevance.py
    completeness.py
    hallucinations.py
```

---

# Evaluation Strategies

---

## Rule Based

Deterministic evaluation.

---

## LLM Judge

Provider based evaluation.

---

## Ragas

Future integration.

---

## DeepEval

Future integration.

---

# Benchmark Runner

```python
GenerationBenchmarkRunner
```

---

# 16. Research Evaluation (Future)

---

# Metrics

- Plan Quality
- Research Coverage
- Reasoning Depth
- Task Completion
- Citation Quality
- Hallucination Rate
- Source Diversity

---

# Benchmark Runner

```python
ResearchBenchmarkRunner
```

---

# 17. Experiment Platform

---

# Purpose

Compare system variations.

Examples:

- model comparisons
- prompt comparisons
- reranker comparisons
- compression comparisons
- planner comparisons

---

# Workflow

```text
Candidate A
Candidate B
Candidate C

↓

Run Benchmark

↓

Collect Metrics

↓

Compare

↓

Winner
```

---

# Example

```text
CrossEncoder

vs

Voyage

↓

MRR
NDCG
Latency
Cost
```

---

# Folder

```text
experiments/

    service.py
    runners/
    reports/
```

---

# 18. Regression Platform

---

# Purpose

Detect quality degradation.

This platform becomes critical once agents exist.

---

# Workflow

```text
Run Benchmark

↓

Load Previous Result

↓

Compare Metrics

↓

Detect Regression

↓

Fail CI
```

---

# Architecture

```text
regression/

    detectors/
    thresholds/
    reports/
```

---

# Example Rules

```python
MRR_DROP_THRESHOLD = 0.05

FAITHFULNESS_THRESHOLD = 0.03

LATENCY_THRESHOLD = 0.25
```

---

# Example

```python
if mrr_drop > 0.05:
    fail()

if faithfulness_drop > 0.03:
    fail()
```

---

# CI Integration

Future:

```text
PR

↓

Run Evaluation

↓

Regression Detection

↓

Pass / Fail
```

---

# 19. Report Platform

---

# Responsibilities

Generate:

- Markdown reports
- JSON reports
- HTML reports (future)

---

# Retrieval Report

```text
Recall
Precision
MRR
NDCG
Latency
Coverage
```

---

# Generation Report

```text
Faithfulness
Groundedness
Completeness
Hallucinations
```

---

# Experiment Report

```text
Winner
Tradeoffs
Recommendations
```

---

# Regression Report

```text
Metric Changes
Threshold Violations
Pass/Fail
```

---

# 20. Artifact Platform Integration

Evaluation should produce immutable artifacts.

---

# Storage

```text
evaluation/

    retrieval/
    generation/
    experiments/
    regression/
```

---

# Example

```text
evaluation/

    retrieval/

        benchmark.json
        report.md

    generation/

        benchmark.json
        report.md

    regression/

        comparison.json
        report.md
```

---

# 21. LangSmith Integration

---

# ResearchMind Owns

- contracts
- runners
- orchestration
- reports
- regressions
- artifacts

---

# LangSmith Owns

- datasets
- experiments
- traces
- comparisons

---

# Future Integrations

- dataset sync
- experiment upload
- benchmark history

---

# 22. Metrics Lifecycle

```text
Dataset

↓

Benchmark Runner

↓

Evaluators

↓

Metrics

↓

Reports

↓

Artifacts

↓

Regression Detection

↓

CI
```

---

# 23. Future Roadmap

---

## Phase 1

Dataset Platform

---

## Phase 2

Retrieval Evaluation

---

## Phase 3

Generation Evaluation

---

## Phase 4

Regression Platform

---

## Phase 5

Experiment Platform

---

## Phase 6

LangSmith Integration

---

## Phase 7

Research Evaluation

---

# 24. Suggested Implementation Order

```text
1. models.py
2. enums.py
3. interfaces.py
4. dataset models
5. retrieval evaluators
6. benchmark runners
7. reports
8. artifacts
9. regression
10. experiments
11. LangSmith integration
```

---

# 25. Exit Criteria

Evaluation Platform is considered complete when:

- Retrieval benchmarks operational
- Generation benchmarks operational
- Regression detection operational
- Reports generated automatically
- Artifacts persisted
- LangSmith integration operational
- CI quality gates possible

---

# Final Vision

```text
NotebookLM++

↓

Perplexity v1

↓

Evaluation Driven AI Platform

↓

Open Deep Research

↓

Manus / Glean
```

Evaluation Platform is the bridge between a RAG application and a production-grade AI Engineering Platform.
