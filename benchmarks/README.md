# ResearchMind AI Engineering Benchmark Platform

## Overview

The Engineering Benchmark Platform provides an offline framework for
measuring and comparing AI components used throughout ResearchMind.

Unlike automated tests, benchmarks do not verify correctness.
Instead, they help AI engineers evaluate competing implementations,
understand trade-offs, and make informed architectural decisions.

Benchmarks are executed manually and are intended for engineering
analysis rather than continuous integration.

---

# Goals

The Benchmark Platform exists to answer questions such as:

- Which chunking strategy performs best?
- Which embedding model produces the best retrieval quality?
- Which reranker improves answer relevance?
- Which retrieval strategy offers the best precision?
- How does the complete AI pipeline perform end-to-end?

Every benchmark should produce reproducible reports that support
engineering decisions with objective measurements.

---

# Philosophy

ResearchMind intentionally separates benchmarking from testing.

## Testing

Purpose:

- Verify software correctness
- Detect regressions
- Ensure components behave as expected

Examples:

- Unit tests
- Integration tests
- End-to-end tests

Testing is executed automatically during development and continuous
integration.

---

## Benchmarking

Purpose:

- Compare alternative AI implementations
- Measure quality
- Measure latency
- Measure resource usage
- Guide architectural decisions

Benchmarks are executed manually and generate engineering reports.

---

# Relationship to Evaluation

ResearchMind contains three complementary evaluation systems.

## 1. Engineering Benchmarks

Audience:

- AI Engineers

Characteristics:

- Offline
- Manual execution
- Deterministic datasets
- Reproducible
- Compares competing implementations

Examples:

- Fixed vs Recursive chunking
- OpenAI vs Voyage embeddings
- Hybrid vs Dense retrieval
- Groq vs OpenAI vs Claude generation quality

---

## 2. Runtime Evaluation

Audience:

- Operations
- Product Engineering

Characteristics:

- Always enabled
- Lightweight
- Measures the configured production pipeline
- Captures latency, throughput, token usage, and quality metrics

Runtime evaluation never experiments with alternative strategies.

---

## 3. Experimentation Platform

Audience:

- AI Engineers
- Research Engineers

Characteristics:

- Optional
- Asynchronous
- Can be enabled or disabled
- Replays production documents through multiple AI strategies
- Produces comparison reports

Experimentation helps determine whether new approaches outperform the
current production configuration.

---

# Repository Structure

```
benchmarks/

    README.md

    runner.py

    common/

        dataset_loader.py
        metrics.py
        report.py
        timer.py

    datasets/

    reports/

    chunking/
    embeddings/
    retrieval/
    reranking/
    generation/
    pipeline/

    regression/

        models.py
        thresholds.py
        detector.py
        report_generator.py
```

---

# Benchmark Workflow

Every benchmark follows the same lifecycle.

```
Dataset
    │
    ▼
Load Documents
    │
    ▼
Execute Candidate Implementations
    │
    ▼
Collect Metrics
    │
    ▼
Generate Reports
    │
    ▼
Engineering Decision
```

The benchmark runner orchestrates execution while individual benchmark
modules provide implementation-specific logic.

---

# Reports

Each benchmark should produce two outputs.

## JSON

Machine-readable benchmark data.

Used by:

- dashboards
- automation
- future visualization tools

---

## Markdown

Human-readable engineering report.

Used for:

- design reviews
- pull requests
- architecture discussions
- engineering documentation

---

# Supported Benchmark Categories

Current:

- Chunking
- Embeddings
- Retrieval (dense vs. sparse vs. hybrid — Recall@K, Precision@K, NDCG@K, MRR, latency)
- Reranking
- Metadata Filtering
- Generation (Groq vs. OpenAI vs. Claude vs. Gemini vs. Ollama — faithfulness, groundedness, relevance, completeness, citation accuracy, hallucination rate, latency; deterministic no-LLM scoring, see `benchmarks/generation/metrics.py`)
- End-to-End AI Pipeline (`benchmarks/pipeline/`, own CLI entry point — see `benchmarks/pipeline/benchmark.py`'s docstring for why it doesn't go through `runner.py`)

Planned:

- Vector Stores

Future benchmark categories can be added without modifying the benchmark
runner.

---

# Design Principles

The Benchmark Platform should remain:

- Provider agnostic
- Framework agnostic
- Deterministic
- Reproducible
- Extensible
- Independent from production infrastructure

Benchmark execution should never require:

- Background workers
- Amazon SQS
- Runtime evaluation
- Experimentation infrastructure

Benchmarks operate directly on canonical platform abstractions.

---

# Usage

Run a benchmark:

```bash
uv run python -m benchmarks.runner chunking --dataset benchmarks/datasets/research-papers
uv run python -m benchmarks.runner embeddings --dataset benchmarks/datasets/research-papers
uv run python -m benchmarks.runner retrieval --dataset benchmarks/datasets/research-papers
uv run python -m benchmarks.runner reranking --dataset benchmarks/datasets/research-papers
uv run python -m benchmarks.runner metadatafiltering --dataset benchmarks/datasets/research-papers
uv run python -m benchmarks.runner generation --dataset benchmarks/datasets/research-papers
```

The generation benchmark scores every `GenerationProvider` that has credentials
configured (see `app/ai/runtime/generation/create.py::create_generation_registry`)
against the query/context/expected-answer/citations dataset in
`benchmarks/datasets/research-papers/generation_queries.json`. Context is
supplied directly by the dataset rather than retrieved live, isolating
generation quality from retrieval quality. A provider that isn't configured
locally (missing API key, or a local Ollama server that isn't running) is
recorded as a zero-scored candidate with its error captured in `notes`
rather than aborting the whole run.

## Regression Checks

Any benchmark can be run with `--check-regression` to compare the new run
against the previously stored `report.json` in the output directory and
fail (non-zero exit code) if a metric crosses its configured threshold
(see `benchmarks/regression/thresholds.py` — e.g. a >0.05 drop in `mrr`, a
>0.03 drop in `faithfulness`, or a >25% relative increase in latency):

```bash
uv run python -m benchmarks.runner retrieval --dataset benchmarks/datasets/research-papers --check-regression
```

This writes `regression.json`/`regression_report.md` alongside the
benchmark's own `report.json`/`report.md`, and is the mechanism by which
this platform satisfies "CI quality gates possible" without depending on
any CI infrastructure itself — a CI job just needs to run the command
above and check the exit code.

The retrieval benchmark builds a dedicated Qdrant collection
(`benchmark_retrieval`, dropped and recreated on every run) from the
benchmark corpus, then evaluates dense (Voyage AI) and sparse (SPLADE)
retrieval against the hand-curated query set in
`benchmarks/datasets/research-papers/retrieval_queries.json`, reporting
Recall@5, Recall@10, Precision@5, MRR, and latency for each candidate.
It requires a reachable Qdrant instance and configured Voyage AI
credentials, and makes real embedding API calls, unlike the chunking and
embeddings benchmarks.

The metadata filtering benchmark (see
[docs/architecture/metadata-filtering.md](../docs/architecture/metadata-filtering.md))
validates `owner_id` payload filtering against its own dedicated
collection (`benchmark_retrieval_filtering`), assigning each benchmark
document a distinct synthetic owner. For dense, sparse, and hybrid
retrieval it compares an unfiltered baseline against a run filtered to
the owner of each query's relevant document, reporting Recall@K,
Precision@K, MRR, and latency for both, plus a `leakage_rate` metric
(the fraction of returned chunks belonging to the wrong owner — expected
to be exactly 0.0). It requires the same Qdrant/Voyage AI setup as the
retrieval benchmark.

---

# Future Vision

The Engineering Benchmark Platform will evolve into a comprehensive
evaluation framework capable of comparing every major AI component used
by ResearchMind.

As the platform grows, benchmark reports will provide objective evidence
to guide architectural evolution, enabling data-driven decisions rather
than relying on intuition or anecdotal observations.
