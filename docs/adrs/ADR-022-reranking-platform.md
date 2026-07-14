# ADR-022: Reranking Platform

**Status:** Accepted
**Date:** 2026-07-14
**Authors:** ResearchMind Team

---

# Context

The Retrieval Platform currently supports:

- Dense Retrieval
- Sparse Retrieval (SPLADE)
- Hybrid Retrieval
- Reciprocal Rank Fusion (RRF)

These approaches optimize primarily for:

```text
Recall
```

While retrieval quality is already strong, embedding similarity and
rank fusion do not always produce the most relevant ordering of results.

Examples:

- ambiguous questions
- multi-topic documents
- long chunks with partial relevance
- semantically similar but contextually incorrect chunks

To improve final answer quality, ResearchMind requires a mechanism to
reorder candidate chunks using deeper semantic understanding.

---

# Problem

Current pipeline:

```text
Question
      │
      ▼
Dense Retrieval
      +
Sparse Retrieval
      │
      ▼
RRF Fusion
      │
      ▼
Final Chunks
```

Limitations:

- ranking errors remain after fusion
- top results may contain partially relevant chunks
- answer quality can degrade despite high recall
- retrieval metrics such as MRR and NDCG remain suboptimal

---

# Decision

Introduce a dedicated **Reranking Platform**.

New pipeline:

```text
Question
      │
      ▼
Dense Retrieval
      +
Sparse Retrieval
      │
      ▼
RRF Fusion
      │
      ▼
Candidate Chunks
      │
      ▼
Reranking Platform
      │
      ▼
Final Chunks
```

Reranking becomes a first-class platform in the knowledge stack.

---

# Architectural Principles

## Separation of Concerns

Reranking shall remain independent from:

- retrieval providers
- fusion strategies
- context construction
- generation

This keeps each platform responsible for a single concern.

---

## Provider Independence

Reranking providers shall be hidden behind canonical interfaces.

Provider-specific APIs must not leak into application layers.

Supported providers:

- CrossEncoder
- Voyage AI

Future:

- Cohere
- Jina
- OpenAI
- BGE Large

---

## Evaluation Driven Development

All reranking improvements must be measurable.

Reranking effectiveness shall be benchmarked using:

- Precision@K
- MRR
- NDCG
- Latency
- Cost

---

# Platform Placement

Reranking shall execute:

```text
After Retrieval Fusion
Before Context Construction
```

Final architecture:

```text
Retrieval
↓
Fusion
↓
Reranking
↓
Context Builder
↓
Generation
```

---

# Rejected Alternatives

---

## Alternative 1

### Rerank Dense Retrieval Only

```text
Dense
↓
Rerank
```

Rejected because:

- sparse retrieval remains untreated
- duplicates infrastructure
- does not benefit hybrid retrieval

---

## Alternative 2

### Rerank Dense and Sparse Separately

```text
Dense
↓
Rerank

Sparse
↓
Rerank
```

Rejected because:

- doubles latency
- doubles cost
- increases complexity
- duplicates work

---

## Alternative 3

### Embed Reranking Inside Retrieval Providers

Rejected because:

- violates separation of concerns
- makes benchmarking difficult
- couples retrieval and reranking

---

# Candidate Strategy

Reranking performs best with larger candidate pools.

Example:

```text
User requests Top 5
```

Pipeline:

```text
Dense Top 25
Sparse Top 25
↓
Fusion
↓
Top 20
↓
Reranking
↓
Top 5
```

---

# Initial Scope

Reranking shall initially support only:

```text
Hybrid Retrieval
```

Dense retrieval and sparse retrieval endpoints will not expose
reranking options during MVP.

Reason:

Hybrid retrieval already provides high recall and benefits the most
from reranking.

---

# Provider Strategy

---

## Development Provider

```text
CrossEncoder
```

Model:

```text
BAAI/bge-reranker-base
```

Advantages:

- local execution
- zero API cost
- easy testing
- deterministic evaluation

---

## Production Provider

```text
Voyage AI
```

Model:

```text
rerank-2
```

Advantages:

- excellent ranking quality
- low latency
- production readiness

---

# Platform Structure

```text
app/ai/knowledge/reranking/

├── create.py
├── registry.py
├── service.py
├── interfaces.py
├── models.py
├── config.py
├── enums.py
├── exceptions.py

└── providers/
    ├── cross_encoder.py
    └── voyage.py
```

---

# Consequences

## Positive

### Better Answer Quality

Improves:

- Precision@K
- MRR
- NDCG

---

### Cleaner Architecture

Maintains separation:

```text
Retrieval
↓
Fusion
↓
Reranking
↓
Context Builder
```

---

### Provider Flexibility

New rerankers can be introduced without changing retrieval.

---

### Evaluation Friendly

Allows benchmarking:

```text
Hybrid

vs

Hybrid + CrossEncoder

vs

Hybrid + Voyage
```

---

## Negative

### Additional Latency

Reranking introduces additional execution time.

Mitigation:

- candidate limits
- configurable providers

---

### Additional Cost

External reranking providers incur API costs.

Mitigation:

- local CrossEncoder provider
- optional reranking

---

# Future Considerations

Potential future enhancements:

---

## Adaptive Reranking

```text
Simple Queries
    ↓
CrossEncoder

Complex Queries
    ↓
Voyage
```

---

## Query Classification

Choose provider dynamically.

---

## Research Runtime Integration

Future flow:

```text
Planner
↓
Retrieval
↓
Fusion
↓
Reranking
↓
Context Builder
↓
Generation
```

---

## Multi-Stage Retrieval

Future:

```text
Retrieval
↓
Reranking
↓
Compression
↓
Context Builder
```

---

# Decision Summary

ResearchMind adopts reranking as a dedicated platform executed:

```text
After Retrieval Fusion
Before Context Construction
```

Initial providers:

- CrossEncoder
- Voyage AI

Initial scope:

```text
Hybrid Retrieval Only
```

This decision improves retrieval precision while preserving clean
architectural boundaries and future extensibility.
