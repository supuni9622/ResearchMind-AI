# ADR-020: Retrieval Evaluation First Development

**Status:** Accepted
**Date:** 2026-07-13
**Decision Makers:** ResearchMind Architecture Team

---

# Context

ResearchMind is being built as a production-grade AI Research & Intelligence Platform.

The Retrieval Platform will evolve through multiple stages:

```text
Dense Retrieval
        ↓
Sparse Retrieval
        ↓
Hybrid Retrieval
        ↓
Reranking
        ↓
Parent/Child Retrieval
        ↓
Query Decomposition
        ↓
Context Compression
```

Each improvement introduces:

- additional complexity
- operational costs
- latency tradeoffs
- maintenance overhead

Without objective evaluation, architectural decisions become subjective and difficult to justify.

Examples of undesirable reasoning:

```text
"This feels better."

"Hybrid seems smarter."

"The results look good."
```

Production retrieval systems require measurable evidence.

---

# Problem

Advanced retrieval techniques often increase complexity significantly while providing little or no measurable benefit.

Examples:

- Hybrid retrieval may not improve results if dense and sparse retrieval behave similarly.
- Reranking may increase latency without meaningful gains.
- Parent/Child retrieval may not improve recall for certain datasets.
- Query decomposition may increase token costs without improving answer quality.

Without benchmarking:

- regressions become difficult to detect
- architectural decisions become opinion-based
- retrieval improvements cannot be quantified
- system complexity continuously grows

---

# Decision

ResearchMind adopts an **Evaluation First Development** principle.

Every retrieval enhancement must demonstrate measurable improvement before becoming part of the canonical architecture.

The workflow becomes:

```text
New Retrieval Technique
            ↓
Implement Independently
            ↓
Benchmark
            ↓
Compare Against Baseline
            ↓
Measure Improvement
            ↓
Adopt or Reject
```

No retrieval enhancement will be accepted based solely on subjective evaluation.

---

# Benchmarking Requirements

Every retrieval capability must be evaluated using benchmark datasets and objective metrics.

---

# Required Metrics

## Recall@K

Measures:

```text
Did we retrieve the relevant information?
```

Metrics:

- Recall@5
- Recall@10
- Recall@20

---

## Precision@K

Measures:

```text
How much irrelevant information was retrieved?
```

Metrics:

- Precision@5
- Precision@10

---

## Mean Reciprocal Rank (MRR)

Measures:

```text
How early does the first relevant result appear?
```

---

## Latency

Measures:

```text
How quickly retrieval completes.
```

Metrics:

- Average latency
- P95 latency
- P99 latency

---

## Cost

Measures:

```text
What is the operational cost of retrieval?
```

Examples:

- embedding cost
- reranking cost
- query decomposition cost

---

# Benchmark Dataset Requirements

Retrieval benchmarking requires curated query datasets.

Datasets should contain multiple query types:

```text
Semantic Questions
Acronyms
Exact Keywords
Rare Entities
Code Queries
Broad Research Questions
```

This ensures retrieval strategies are evaluated across realistic scenarios.

---

# Architectural Principle

The following principle is frozen:

> Retrieval improvements must be measurable.

If an enhancement cannot demonstrate measurable value, it should not become part of the production architecture.

---

# Adoption Criteria

A retrieval enhancement may be adopted if it demonstrates improvements in one or more areas:

- higher Recall@K
- higher Precision@K
- improved MRR
- lower latency
- lower operational cost
- better user experience

Tradeoffs are allowed if justified.

Example:

```text
+15% Recall
+40ms latency
```

may still be considered beneficial.

---

# Initial Benchmark Scope

The initial benchmark comparison includes:

```text
Dense Retrieval
vs
Sparse Retrieval
```

This benchmark establishes the baseline for future improvements.

Future comparisons include:

```text
Dense vs Sparse vs Hybrid
Hybrid vs Hybrid + Reranker
Parent/Child Retrieval
Query Decomposition
Context Compression
```

---

# Evaluation Lifecycle

The long-term retrieval evaluation workflow becomes:

```text
Dataset
      ↓
Retriever
      ↓
Metrics
      ↓
Reports
      ↓
Architecture Decision
```

Evaluation becomes a first-class platform capability.

---

# Consequences

## Positive

### Objective Architecture Decisions

Retrieval improvements become evidence-based.

---

### Regression Detection

Future changes can be compared against historical benchmarks.

---

### Better Portfolio Signal

Demonstrates understanding of production AI engineering practices.

---

### Lower Architectural Risk

Avoids unnecessary complexity.

---

### Enables Continuous Improvement

ResearchMind can iteratively improve retrieval quality while maintaining measurable standards.

---

## Negative

### Additional Development Time

Benchmark datasets and evaluators require additional effort.

---

### Requires Dataset Maintenance

Evaluation datasets must evolve alongside the platform.

---

### Requires Continuous Benchmark Execution

Changes to retrieval may require re-running evaluations.

---

# Future Extensions

This principle will eventually expand into the Evaluation Platform.

Future capabilities include:

- NDCG
- Reranker Evaluation
- Hallucination Evaluation
- Groundedness
- Faithfulness
- Citation Accuracy
- Cost Analysis
- Agent Evaluation
- End-to-End Research Evaluation

---

# Status

This decision is considered frozen.

Evaluation First Development is now an architectural principle of ResearchMind.

All future retrieval improvements must demonstrate measurable value before adoption.
