# Retrieval Benchmarking Strategy

**Status:** Accepted
**Phase:** Retrieval Platform
**Date:** 2026-07-13

---

# Purpose

Before implementing Hybrid Retrieval, ResearchMind must benchmark individual retrieval strategies independently.

The purpose of benchmarking is to:

- understand strengths and weaknesses of Dense Retrieval
- understand strengths and weaknesses of Sparse Retrieval
- validate whether Hybrid Retrieval provides measurable improvements
- establish the initial Evaluation Platform dataset
- create reproducible retrieval quality measurements

This document freezes the initial retrieval evaluation methodology.

---

# Evaluation Philosophy

Retrieval systems should not be evaluated subjectively.

This:

```text
"This looks good."
```

is not sufficient.

Instead, retrieval quality must be measured using:

```text
Queries
        ↓
Expected Relevant Results
        ↓
Metrics
        ↓
Comparison
```

---

# Evaluation Scope

Initial benchmarking covers:

## Dense Retrieval

```text
Question
      ↓
Voyage Query Embedding
      ↓
Qdrant Dense Search
```

---

## Sparse Retrieval

```text
Question
      ↓
FastEmbed SPLADE Query Embedding
      ↓
Qdrant Sparse Search
```

---

## Hybrid Retrieval

Hybrid benchmarking will be added later after both individual retrievers are validated.

---

# Benchmark Dataset

ResearchMind requires a manually curated benchmark dataset.

---

# Initial Dataset Size

Recommended:

```text
20–50 queries
```

This size is sufficient to:

- validate retrieval quality
- identify weaknesses
- compare retrieval strategies

Larger datasets can be introduced later.

---

# Dataset Location

```text
evaluation/
└── datasets/
    └── retrieval_queries.json
```

---

# Dataset Format (Version 1)

Initial evaluation will use:

## Document-Level Relevance

Example:

```json
[
  {
    "query_id": "q1",
    "query": "What is Retrieval Augmented Generation?",
    "relevant_documents": [
      "LLM_RESEARCH.pdf"
    ]
  }
]
```

This minimizes dataset creation effort.

---

# Dataset Format (Version 2)

Future improvement:

## Chunk-Level Relevance

Example:

```json
[
  {
    "query_id": "q1",
    "query": "What is Retrieval Augmented Generation?",
    "relevant_chunk_ids": [
      "chunk_123",
      "chunk_124"
    ]
  }
]
```

Chunk-level evaluation provides significantly better accuracy.

---

# Query Categories

The benchmark dataset must contain multiple query types.

Avoid only testing semantic questions.

---

## Category 1 — Semantic Questions

Examples:

```text
What are the limitations of retrieval systems?
Explain retrieval augmentation techniques.
```

Expected Winner:

```text
Dense Retrieval
```

---

## Category 2 — Acronyms

Examples:

```text
RAG
SPLADE
HNSW
```

Expected Winner:

```text
Sparse Retrieval
```

---

## Category 3 — Exact Keywords

Examples:

```text
Voyage-3-lite
FastEmbedSparseEmbeddingProvider
```

Expected Winner:

```text
Sparse Retrieval
```

---

## Category 4 — Rare Entities

Examples:

```text
query_points
BM42
```

Expected Winner:

```text
Sparse Retrieval
```

---

## Category 5 — Code Queries

Examples:

```text
How does query_points work?
What is FastEmbedSparseEmbeddingProvider?
```

Expected Winner:

```text
Sparse Retrieval
```

---

## Category 6 — Broad Research Questions

Examples:

```text
Explain document retrieval architectures.
```

Expected Winner:

```text
Dense Retrieval
```

---

# Recommended Dataset Distribution

```text
5 Semantic Queries
5 Acronym Queries
5 Exact Keyword Queries
5 Code / Rare Entity Queries
```

Minimum:

```text
20 Queries
```

---

# Benchmark Metrics

---

# Recall@K

Measures:

```text
How much relevant information was retrieved?
```

Formula:

```text
Relevant Retrieved
────────────────────
All Relevant Results
```

Metrics:

- Recall@5
- Recall@10
- Recall@20

---

# Precision@K

Measures:

```text
How much irrelevant information was retrieved?
```

Formula:

```text
Relevant Retrieved
───────────────────
Retrieved Results
```

Metrics:

- Precision@5
- Precision@10

---

# Mean Reciprocal Rank (MRR)

Measures:

```text
How early does the first relevant result appear?
```

This metric is extremely important for RAG systems.

---

# NDCG

Measures:

```text
How well are results ranked?
```

This metric can be introduced later.

Not required for initial benchmarking.

---

# Latency

Measures:

```text
How quickly retrieval completes.
```

Metrics:

- Average latency
- P95 latency
- P99 latency

---

# Cost

Measures:

```text
Embedding cost per query.
```

Dense retrieval uses paid embeddings.

Sparse retrieval uses local inference.

---

# Initial Benchmark Matrix

| Metric | Dense | Sparse |
|---------|--------|---------|
| Recall@5 | ✅ | ✅ |
| Recall@10 | ✅ | ✅ |
| Precision@5 | ✅ | ✅ |
| MRR | ✅ | ✅ |
| Latency | ✅ | ✅ |
| Cost | ✅ | ✅ |

---

# Example Benchmark Output

## Dense Retrieval

```text
Recall@5       0.74
Recall@10      0.83
Precision@5    0.61
MRR            0.72
Latency        430ms
```

---

## Sparse Retrieval

```text
Recall@5       0.62
Recall@10      0.70
Precision@5    0.78
MRR            0.81
Latency        75ms
```

---

# Interpretation

Typical observations:

Dense Retrieval:

- better semantic understanding
- better broad question coverage

Sparse Retrieval:

- better exact matching
- better acronyms
- better rare entities
- better code search

These complementary strengths justify Hybrid Retrieval.

---

# Hybrid Retrieval Decision Gate

Hybrid Retrieval should only be implemented if:

```text
Dense Results != Sparse Results
```

If both retrievers produce nearly identical outputs, Hybrid Retrieval provides limited value.

---

# Benchmark Output Storage

```text
evaluation/

datasets/
    retrieval_queries.json

benchmarks/
    dense_results.json
    sparse_results.json

reports/
    dense_vs_sparse.md
```

---

# Future Evaluation Expansion

The Evaluation Platform will eventually include:

- Hybrid improvements
- Reranker improvements
- Recall improvements
- NDCG
- Citation accuracy
- Hallucination evaluation
- Groundedness
- Faithfulness
- Cost analysis
- Parent/Child retrieval evaluation
- Query decomposition evaluation

---

# Architectural Decision

ResearchMind will benchmark every retrieval improvement before adoption.

This includes:

- Dense Retrieval
- Sparse Retrieval
- Hybrid Retrieval
- Reranking
- Parent/Child Retrieval
- Query Decomposition

Evaluation-first development is a frozen architectural principle.

---

# Current Status

```text
Dense Retrieval       ✅ Implemented
Sparse Retrieval      ✅ Implemented
Hybrid Retrieval      ⏳ Pending Benchmark Validation
Evaluation Platform   ⏳ Planned
```

Sparse retrieval performed similarly to dense retrieval on the initial benchmark dataset while being significantly faster.

However, the benchmark dataset is small and uses document-level relevance, likely inflating retrieval metrics.

Future benchmarking should introduce:

- larger datasets
- chunk-level relevance
- harder semantic queries
