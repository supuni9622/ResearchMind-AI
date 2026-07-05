# Evaluation Strategy

**Status:** Living Architecture Document

---

# Overview

ResearchMind evaluates AI quality through three complementary
evaluation layers.

Each layer serves a different audience, operates at a different stage of
the development lifecycle, and answers different engineering questions.

These layers are intentionally separated to keep production systems
simple while enabling continuous improvement of the AI platform.

---

# Why Three Evaluation Layers?

No single evaluation mechanism can satisfy every engineering need.

For example:

- Developers need repeatable regression tests.
- Operations teams need visibility into production behaviour.
- AI engineers need to compare alternative strategies.

Attempting to solve all of these problems using a single evaluation
system would result in unnecessary complexity.

Instead, ResearchMind separates evaluation into three independent
layers.

---

# Evaluation Layers

| Layer | Audience | Purpose |
|-------|----------|---------|
| Engineering Benchmarks | Developers | Prevent regressions and validate implementations |
| Runtime Evaluation | Operations & Product | Observe production quality, latency, and cost |
| Experimentation | AI Engineers | Compare alternative strategies and guide architectural decisions |

Although all three produce measurements, they exist for different
reasons and should not be combined.

---

# Layer 1 — Engineering Benchmarks

## Purpose

Engineering Benchmarks validate implementations during development.

They ensure new code does not regress existing functionality and provide
a repeatable way to compare implementations.

Benchmarks are deterministic and use repository-owned datasets.

---

## Audience

Developers

---

## Execution

Engineering Benchmarks execute during development and continuous
integration.

Typical workflow

```
Developer

↓

Run Tests

↓

Benchmark Dataset

↓

Assertions

↓

Pass / Fail
```

---

## Characteristics

- Deterministic
- Fast
- Repeatable
- Repository-owned
- Executed during CI

---

## Inputs

Benchmark datasets stored inside the repository.

Examples

```
benchmarks/

    documents/

    questions/

    expected/
```

These datasets remain stable over time so that implementations can be
compared across releases.

---

## Example Questions

Examples include:

- Did Recursive produce fewer paragraph splits than Fixed?
- Did retrieval quality improve?
- Did latency regress?
- Did a provider change break existing behaviour?

---

## Outputs

Engineering Benchmarks primarily produce:

- Test results
- Benchmark reports
- Continuous Integration feedback

They are not intended for production use.

---

# Layer 2 — Runtime Evaluation

## Purpose

Runtime Evaluation continuously observes the configured production AI
pipeline.

It evaluates only the pipeline that users actually experience.

Runtime Evaluation never executes alternative strategies.

---

## Audience

Operations

Product Engineering

Platform Engineering

---

## Execution

Runtime Evaluation executes during every production pipeline run.

```
Production Pipeline

↓

Processing

↓

Chunking

↓

Embedding

↓

Retrieval

↓

Runtime Report
```

---

## Characteristics

- Always enabled
- Low overhead
- Non-intrusive
- Production only
- Observational

---

## Example Metrics

Processing

- Processing latency
- Parser used

Chunking

- Strategy
- Chunk count
- Average chunk size

Embedding

- Provider
- Model
- Embedding latency
- Cost

Retrieval

- Retrieval latency
- Top-K

LLM

- Token usage
- Cost
- Groundedness

Pipeline

- Total latency
- Total cost
- Overall health

---

## Outputs

Runtime Evaluation produces production reports.

Example

```
documents/

    {owner_id}/

        {document_id}/

            evaluation/

                runtime/

                    report.json
```

These reports support operational monitoring and internal dashboards.

---

# Layer 3 — Experimentation

## Purpose

Experimentation evaluates alternative AI strategies.

Unlike Runtime Evaluation, Experimentation intentionally executes
multiple competing implementations in order to compare their behaviour.

Its purpose is to improve the AI platform rather than monitor it.

---

## Audience

AI Engineers

Research Engineers

Platform Architects

---

## Execution

Experimentation executes asynchronously.

```
ProcessedDocument

↓

Experiment Queue

↓

Experiment Worker

↓

Multiple Strategies

↓

Comparison

↓

Recommendation

↓

Experiment Report
```

---

## Characteristics

- Optional
- Configurable
- Asynchronous
- Potentially expensive
- Internal only

---

## Examples

Chunking

- Fixed
- Recursive
- Markdown
- Hierarchical
- Semantic
- LLM

Embedding

- Voyage AI
- OpenAI
- Sentence Transformers
- BGE

Retrieval

- Dense
- Sparse
- Hybrid

Pipeline

Complete end-to-end pipeline comparisons.

---

## Outputs

Experiment reports.

Example

```
documents/

    {owner_id}/

        {document_id}/

            experimentation/

                chunking/

                    report.json

                embedding/

                    report.json

                retrieval/

                    report.json

                pipeline/

                    report.json
```

Experiment reports contain comparisons, recommendations, and engineering
insights.

---

# Comparison of the Three Layers

| Characteristic | Engineering Benchmarks | Runtime Evaluation | Experimentation |
|---------------|------------------------|--------------------|-----------------|
| Runs in CI | ✅ | ❌ | ❌ |
| Runs in Production | ❌ | ✅ | Optional |
| Uses Repository Datasets | ✅ | ❌ | ❌ |
| Uses Real User Documents | ❌ | ✅ | ✅ |
| Executes Multiple Strategies | ❌ | ❌ | ✅ |
| Produces Recommendations | ❌ | ❌ | ✅ |
| Observes Production Pipeline | ❌ | ✅ | ❌ |
| Prevents Regressions | ✅ | ❌ | ❌ |
| Supports Operational Monitoring | ❌ | ✅ | ❌ |
| Supports Engineering Decisions | Limited | Limited | ✅ |

---

# Design Principles

## Separation of Responsibilities

Each evaluation layer owns a single responsibility.

Engineering Benchmarks validate implementations.

Runtime Evaluation observes production.

Experimentation improves future implementations.

No layer should assume the responsibilities of another.

---

## Shared Canonical Models

All evaluation layers consume the same canonical ResearchMind models.

Examples

- ProcessedDocument
- ChunkArtifact
- EmbeddingArtifact
- RetrievalArtifact

This ensures evaluation remains independent of third-party AI
frameworks.

---

## Independent Evolution

The three evaluation layers evolve independently.

New metrics added to Runtime Evaluation do not require changes to
Engineering Benchmarks.

New Experimentation capabilities do not affect production systems.

---

## Evidence-Based Engineering

Architectural decisions should be guided by measurable evidence rather
than intuition.

ResearchMind continuously collects objective measurements to support:

- Provider selection
- Performance optimization
- Quality improvements
- Regression detection
- Long-term platform evolution

---

# Long-Term Vision

As ResearchMind evolves, evaluation becomes a first-class engineering
capability rather than a collection of tests.

Engineering Benchmarks ensure correctness.

Runtime Evaluation ensures production health.

Experimentation drives continuous improvement.

Together these layers enable ResearchMind to make AI engineering
decisions based on measurable evidence while keeping production systems
stable, observable, and maintainable.
