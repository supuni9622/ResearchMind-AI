# Engineering Journal
# Phase 3 — Milestone 3.1
# Retrieval Foundation

**Status:** Completed

**Date:** 2026-07-13

---

# Objective

Build the first production retrieval capability for ResearchMind.

Goal:

```text
Question
    ↓
Semantic Retrieval
    ↓
Top-K Chunks
```

This milestone represents the transition from a Knowledge Ingestion Platform into an AI Runtime Platform.

---

# Scope

Implemented:

- Query embeddings
- Dense retrieval
- Retrieval platform architecture
- Retrieval API
- Query embedding cache
- Qdrant retrieval provider
- Runtime metrics

Not included:

- Sparse retrieval
- Hybrid retrieval
- Metadata filtering
- Reranking
- Context compression
- Generation

---

# Final Architecture

```text
Question
      ↓
Query Validation
      ↓
Query Normalization
      ↓
Query Embedding Service
      ↓
Embedding Cache
      ↓
Qdrant Retrieval Provider
      ↓
Top-K Chunks
      ↓
Retrieve API
```

---

# Platforms Introduced

## Retrieval Platform

```text
retrieval/

├── base.py
├── config.py
├── create.py
├── enums.py
├── exceptions.py
├── interfaces.py
├── models.py
├── registry.py
├── service.py

├── providers/
│   └── qdrant.py

└── query/
    └── service.py
```

---

# Major Architectural Decisions

---

## ADR-001
## Retrieval owns search.

Decision:

Create a dedicated Retrieval Platform.

Avoid using Vector Store Platform directly.

### Reasoning

Vector Store responsibilities:

- collection lifecycle
- indexing
- deletion

Retrieval responsibilities:

- searching
- filtering
- hybrid search
- reranking integration
- retrieval strategies

Keeping them separate maintains platform boundaries.

Decision Status:

✅ Accepted

---

## ADR-002
## Query embeddings are separate from document embeddings.

Decision:

Introduce:

```text
QueryEmbeddingService
```

instead of extending EmbeddingService.

### Reasoning

Document embeddings and query embeddings have different requirements.

Examples:

Voyage:

```python
input_type="document"
input_type="query"
```

Future capabilities:

- HyDE
- Query rewriting
- Query decomposition
- Search-specific models

Decision Status:

✅ Accepted

---

## ADR-003
## Query embedding cache implemented immediately.

Decision:

Implement query embedding cache.

Postpone retrieval cache.

### Reasoning

Query embeddings are:

- expensive
- frequently repeated
- easy to invalidate

Retrieval cache requires:

- knowledge versioning
- invalidation strategies
- filter awareness

Decision Status:

✅ Accepted

---

## ADR-004
## Retrieval Platform owns runtime metrics.

Decision:

Latency measurements belong to RetrievalService.

Provider implementations remain simple.

Decision Status:

✅ Accepted

---

## ADR-005
## Retrieval provider directly uses Qdrant search APIs.

Decision:

Implement:

```text
QdrantRetrievalProvider
```

Reason:

Allows future support for:

- dense search
- sparse search
- hybrid search
- parent-child retrieval

without modifying RetrievalService.

Decision Status:

✅ Accepted

---

# Issues Encountered

---

## Issue 1

### Qdrant SDK API Change

Problem:

```python
AsyncQdrantClient.search()
```

was removed/deprecated.

Solution:

Migrated to:

```python
query_points()
```

Decision:

Use:

```python
response = await client.query_points(...)
points = response.points
```

---

## Issue 2

### Retrieved chunks had empty content.

Problem:

Qdrant payloads did not store chunk text.

Response:

```json
{
  "content": ""
}
```

Root Cause:

`VectorPayload` lacked:

```python
content: str
```

Fix:

- add content field
- update indexing payload
- reindex knowledge base

Decision Status:

✅ Fixed

---

# API Introduced

## POST /api/v1/retrieve

Request:

```json
{
  "query": "what is RAG?",
  "top_k": 5
}
```

Response:

```json
{
  "query": "what is RAG?",
  "duration_ms": 152,
  "total_chunks": 5,
  "chunks": [...]
}
```

This is the first production-consumable AI API in ResearchMind.

---

# Benchmarks

Current latency:

~560ms

Includes:

- query embedding
- Voyage API call
- Qdrant retrieval

Expected after query embedding cache:

~100–250ms

---

# Milestone Completion Criteria

Completed:

✅ Retrieval models

✅ Provider abstraction

✅ Query embedding service

✅ Query embedding cache

✅ Qdrant retrieval provider

✅ Retrieval service

✅ Dependency injection

✅ Retrieval API

✅ Runtime metrics

✅ Payload fixes

✅ End-to-end testing

---

# Current AI Pipeline

```text
Upload
    ↓
Processing
    ↓
Chunking
    ↓
Embeddings
    ↓
Indexing
    ↓
Qdrant
    ↓
Retrieval
```

ResearchMind now officially supports semantic retrieval.

---

# Next Milestone

## Phase 3.2

Sparse Retrieval

Implementation:

```text
Question
      ↓
SPLADE Query Embedding
      ↓
Qdrant Sparse Search
      ↓
Top-K Chunks
```

Future:

```text
Dense
   +
Sparse
      ↓
Hybrid Retrieval
```

---

# Lessons Learned

1. Retrieval requires chunk text in vector payloads.
2. Query embeddings should be treated as a separate capability.
3. Platform boundaries remain valuable.
4. Query embedding cache provides immediate benefits.
5. Building vertical slices first continues to validate the architecture.
