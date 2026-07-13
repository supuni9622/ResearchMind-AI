# Engineering Journal
# Phase 3 — Milestone 3.3
# Hybrid Retrieval

**Status:** Completed

**Date:** 2026-07-13

---

# Objective

Implement Hybrid Retrieval for ResearchMind.

Goal:

```text
Question
      ↓
Dense Retrieval
      ↓
Sparse Retrieval
      ↓
Fusion
      ↓
Top-K Chunks
```

This milestone introduces the first production retrieval strategy that combines multiple retrieval techniques.

---

# Motivation

Dense retrieval and sparse retrieval have complementary strengths.

Dense retrieval excels at:

- semantic understanding
- paraphrases
- broad concepts
- conceptual similarity

Sparse retrieval excels at:

- exact keywords
- acronyms
- rare entities
- code search
- technical terms

Hybrid retrieval combines both strengths.

---

# Final Architecture

```text
Question
      ↓
Query Validation
      ↓
Query Normalization
      ↓
Dense Query Embedding
      ↓
Dense Search
                ↘
                 Fusion (RRF)
                ↗
Sparse Search
      ↓
Sparse Query Embedding
      ↓
Top-K Chunks
```

---

# New Components

## Fusion Package

```text
retrieval/

fusion/

├── interfaces.py
├── models.py
├── rrf.py
├── service.py
```

---

# Implemented Features

## Reciprocal Rank Fusion (RRF)

Implemented:

```text
score += 1 / (k + rank)
```

Default:

```text
k = 60
```

---

## Hybrid Retrieval Service

Implemented:

```text
search_hybrid()
```

Workflow:

```text
Dense Search
        +
Sparse Search
        ↓
Fusion
```

---

## Hybrid API

Implemented:

```http
POST /retrieve/hybrid
```

---

# Architectural Decisions

---

# ADR-001

## Hybrid Retrieval uses Application-Level Fusion

Decision:

Fusion occurs inside ResearchMind rather than inside Qdrant.

---

### Alternatives Considered

### Qdrant Native Hybrid Search

Rejected for now.

Reasons:

- reduced observability
- harder benchmarking
- difficult experimentation
- harder debugging

---

### Application-Level Fusion

Accepted.

Benefits:

- full visibility into dense results
- full visibility into sparse results
- benchmarking flexibility
- future weighted fusion support
- easier experimentation

---

Decision Status:

✅ Accepted

---

# ADR-002

## Reciprocal Rank Fusion selected as canonical fusion strategy.

Reasons:

- robust
- industry standard
- score normalization unnecessary
- easy to benchmark
- widely used in production systems

Used by:

- Elasticsearch
- OpenSearch
- Azure AI Search

Decision Status:

✅ Accepted

---

# ADR-003

## Internal candidate expansion.

Decision:

Hybrid retrieval internally retrieves:

```text
top_k * 2
```

before fusion.

Example:

User:

```text
top_k = 5
```

Internally:

```text
dense_top_k = 10
sparse_top_k = 10
```

---

Reasoning:

Fusion requires a larger candidate pool.

Without expansion:

```text
Dense
A B C D E

Sparse
A B C D E
```

Fusion becomes ineffective.

Decision Status:

✅ Accepted

---

# Benchmark Findings

Initial benchmark dataset:

```text
5 documents
20 queries
```

Results:

### Dense

```text
Recall@10      1.0
MRR            0.95
Latency        ~322ms
```

### Sparse

```text
Recall@10      1.0
MRR            0.975
Latency        ~12ms
```

---

# Observations

Current benchmark dataset is likely too small.

Reasons:

- small document set
- document-level relevance
- limited query difficulty

Future evaluation should include:

- more documents
- chunk-level relevance
- harder semantic queries

---

# Hybrid Retrieval Validation

Example:

Query:

```text
tell me about llm
```

Returned:

- definitions
- hallucinations
- productivity studies
- citations

This validates:

- dense retrieval contributions
- sparse retrieval contributions
- successful fusion

---

# Current Retrieval Stack

```text
Question
      ↓
Dense Search
      ↓
Sparse Search
      ↓
RRF Fusion
      ↓
Top-K Chunks
```

---

# Remaining Retrieval Roadmap

Remaining:

```text
Metadata Filtering
Reranking
Context Compression
Parent/Child Retrieval
Parallel Retrieval
Query Decomposition
```

---

# Current Platform Status

Completed:

```text
Dense Retrieval             ✅
Sparse Retrieval            ✅
Hybrid Retrieval            ✅
Retrieval Benchmarking      ✅
```

---

# Updated Architecture

```text
Upload Platform
      ↓
Processing Platform
      ↓
Chunking Platform
      ↓
Embedding Platform
      ↓
Vector Store Platform
      ↓
Retrieval Platform
            ├── Dense
            ├── Sparse
            └── Hybrid
```

---

# Lessons Learned

1. Dense and sparse retrieval are complementary.
2. RRF provides robust fusion without score normalization.
3. Application-level fusion greatly improves observability.
4. Benchmark datasets must evolve with platform maturity.
5. Hybrid retrieval significantly improves retrieval architecture quality.

---

# Next Milestone

## Metadata Filtering

Goal:

```text
Question
      ↓
Hybrid Retrieval
      ↓
Metadata Filters
      ↓
Top-K Chunks
```

Support:

- document_id
- owner_id
- filename
- language
- tags
- future filters
