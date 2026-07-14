# Reranking Platform Architecture

**Status:** 🚧 In Progress
**Phase:** Milestone 2.7.2 — Retrieval Platform
**Last Updated:** 2026-07-14

---

# Purpose

The Reranking Platform improves retrieval quality by reordering
retrieved candidate chunks using more expensive relevance models.

Instead of relying solely on embedding similarity, rerankers
perform deep semantic relevance scoring between:

```text
(Query, Retrieved Chunk)
```

This significantly improves answer quality, especially for:

- ambiguous queries
- long documents
- multi-topic knowledge bases
- hybrid retrieval pipelines

---

# Motivation

Embedding similarity retrieval is optimized for:

```text
Recall
```

but not necessarily:

```text
Precision
```

Reranking improves:

- Precision@K
- MRR
- NDCG

while usually having minimal impact on Recall.

---

# Architectural Principles

## Separation of Concerns

Reranking is implemented as an independent platform.

```text
Retrieval
↓
Fusion
↓
Reranking
↓
Context Builder
```

instead of:

```text
Dense Search
↓
Rerank

Sparse Search
↓
Rerank
```

This minimizes cost and latency.

---

## Provider Independence

The platform exposes canonical models and interfaces.

Provider-specific implementations are isolated.

Supported providers:

- CrossEncoder
- Voyage AI

Future:

- Cohere Rerank
- Jina AI
- OpenAI
- BGE Reranker Large

---

# High Level Architecture

```text
User Query
      │
      ▼
Hybrid Retrieval
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
Top Relevant Chunks
```

---

# Retrieval Flow

```text
Question
      │
      ▼
Dense Search
      +
Sparse Search
      │
      ▼
Reciprocal Rank Fusion
      │
      ▼
Top Candidate Chunks
      │
      ▼
Reranking
      │
      ▼
Final Chunks
```

---

# Candidate Retrieval Strategy

Reranking works best with larger candidate pools.

Example:

```text
User Requests Top 5
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

# Platform Structure

```text
app/ai/knowledge/reranking/

├── create.py
├── registry.py
├── service.py
├── interfaces.py
├── models.py
├── enums.py
├── config.py
├── exceptions.py

└── providers/
    ├── cross_encoder.py
    └── voyage.py
```

---

# Canonical Models

## RerankingRequest

```python
class RerankingRequest:

    query: str

    chunks: list[RetrievedChunk]

    top_k: int
```

---

## RerankingResult

```python
class RerankingResult:

    chunks: list[RerankedChunk]

    duration_ms: float
```

---

# Providers

---

# CrossEncoder Provider

## Purpose

Local reranking provider.

Suitable for:

- development
- testing
- offline evaluation
- benchmarking

---

## Model

Default:

```text
BAAI/bge-reranker-base
```

Alternative:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

---

## Flow

```text
Query
+
Chunk
↓
CrossEncoder
↓
Relevance Score
```

---

## Advantages

✅ Local

✅ No API costs

✅ Easy testing

❌ Slower

❌ Higher memory usage

---

# Voyage AI Provider

## Purpose

Production-grade reranking provider.

---

## Model

Default:

```text
rerank-2
```

---

## Flow

```text
Query
+
Documents
↓
Voyage API
↓
Relevance Scores
```

---

## Advantages

✅ Excellent quality

✅ Fast

✅ Production ready

❌ Paid API

❌ External dependency

---

# Integration Strategy

Reranking is currently applied only to:

```text
Hybrid Retrieval
```

and not:

```text
Dense Retrieval
Sparse Retrieval
```

Reason:

Hybrid retrieval already provides strong recall.

Reranking improves precision without doubling costs.

---

# API Example

```json
{
  "query": "What is metadata filtering?",
  "top_k": 5,
  "filters": {},
  "rerank": true
}
```

---

# Example Pipeline

```text
Question:
"What is RAG?"

↓

Hybrid Retrieval

↓

25 Candidate Chunks

↓

CrossEncoder

↓

Top 5 Chunks
```

---

# Evaluation Metrics

Reranking primarily improves:

- Precision@5
- Precision@10
- MRR
- NDCG@5
- NDCG@10

Metrics to monitor:

```text
Recall@5
MRR
NDCG@5
Latency
Cost
```

---

# Configuration

Settings:

```python
cross_encoder_model

voyage_api_key

voyage_reranker_model
```

---

# Current Status

```text
Milestone 2.7.2

Status:

🚧 In Progress
```

---

# Exit Criteria

- CrossEncoder Provider
- Voyage Provider
- Registry
- Service
- Dependency Injection
- Hybrid Integration
- Tests
- Benchmarks
- Documentation

---

# Future Enhancements

## Additional Providers

```text
Cohere
Jina
OpenAI
BGE Large
```

---

## Adaptive Reranking

Potential future optimization:

```text
Short Queries
    ↓
CrossEncoder

Long Research Queries
    ↓
Voyage
```

---

## Agent Integration

Future Research Runtime:

```text
Planner
↓
Retrieval
↓
Reranking
↓
Context Builder
↓
Generation
```

---

# Architectural Decision

Reranking is intentionally implemented as a dedicated platform:

```text
Retrieval
↓
Fusion
↓
Reranking
↓
Context Builder
```

This preserves:

- clean architecture
- provider independence
- evaluation capabilities
- future extensibility
