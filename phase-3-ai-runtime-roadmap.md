# ResearchMind AI — Phase 3 Roadmap
## Retrieval & AI Runtime Roadmap (MVP)

**Status:** Frozen (v1.0)

**Last Updated:** 2026-07-08

---

# Purpose

The Knowledge Ingestion Platform is now complete.

```
Upload
↓
Processing
↓
Chunking
↓
Embedding
↓
Indexing
↓
Vector Store (Qdrant)
```

ResearchMind now transitions from a **Knowledge Ingestion Platform** into an **AI Research Platform**.

The next stages focus on consuming knowledge rather than producing it.

---

# Engineering Principles

This roadmap follows the project's established engineering philosophy.

- Build complete vertical slices.
- Every platform owns one business capability.
- Canonical domain models only.
- Provider independence.
- Production-first engineering.
- Evaluation-driven development.
- Documentation-first.
- Freeze architectural decisions once validated.

---

# Overall AI Pipeline

```
                    Upload Platform
                          │
                          ▼
                 Processing Platform
                          │
                          ▼
                 Chunking Platform
                          │
                          ▼
                Embedding Platform
                          │
                          ▼
               Vector Store Platform
                          │
                          ▼
                Retrieval Platform
                          │
                          ▼
               Reranking Platform
                          │
                          ▼
             Context Building Platform
                          │
                          ▼
                Generation Platform
                          │
                          ▼
                Evaluation Platform
                          │
                          ▼
                Agentic AI Platform
```

---

# Phase 3.1 — Retrieval Foundation

## Goal

Build the first production-ready semantic retrieval pipeline.

## Responsibilities

### Query Processing

- Query validation
- Query normalization
- Query embedding

### Search Engine

- Dense semantic retrieval

### Retrieval Strategy

- Standard similarity search

---

## Workflow

```
Question
      │
      ▼
Query Processing
      │
      ▼
Voyage Query Embedding
      │
      ▼
Qdrant Dense Search
      │
      ▼
Top-K Results
```

---

## Deliverables

- Retrieval models
- Retrieval service
- Qdrant retrieval provider
- Registry
- Composition root
- Dense retrieval API
- Tests
- Documentation

---

## API

```
POST /retrieve
```

Returns

- Retrieved chunks
- Scores
- Metadata

---

# Phase 3.2 — Sparse Retrieval

## Goal

Add lexical retrieval using FastEmbed SPLADE.

---

## Workflow

```
Question
      │
      ▼
SPLADE Query Embedding
      │
      ▼
Qdrant Sparse Search
      │
      ▼
Top-K Results
```

---

## Deliverables

- Sparse retriever
- Sparse query embedding
- Sparse search
- Evaluation

---

# Phase 3.3 — Hybrid Retrieval

## Goal

Combine dense and sparse retrieval.

---

## Workflow

```
Dense Search
      +

Sparse Search
      │
      ▼
Reciprocal Rank Fusion (RRF)
      │
      ▼
Top Results
```

---

## Deliverables

- Hybrid retrieval
- RRF
- Hybrid evaluation

---

# Phase 3.4 — Retrieval Strategies

## Goal

Support advanced retrieval strategies.

---

## Standard Retrieval

```
Query

↓

Vector Search

↓

Top-K
```

---

## Parent / Child Retrieval

```
Parent Documents

↓

Child Chunks

↓

Retrieve Parents
```

---

## Parallel Retrieval

```
Query

↓

Multiple Retrieval Pipelines

↓

Merge Results
```

---

## Query Decomposition

```
Complex Question

↓

Sub Questions

↓

Retrieve Separately

↓

Merge Results
```

---

## Deliverables

- Parent/Child retrieval
- Parallel retrieval
- Query decomposition

---

# Phase 3.5 — Result Processing

## Goal

Improve retrieval quality before reranking.

---

## Features

### Metadata Filtering

Support

- owner_id
- workspace_id
- document_id
- filename
- language
- tags

---

### Reciprocal Rank Fusion (RRF)

Merge multiple retrieval strategies.

---

### Top-K Selection

Reduce

```
100

↓

50

↓

20
```

before reranking.

---

## Deliverables

- Metadata filtering
- Top-K selection
- Result processing pipeline

---

# Phase 3.6 — Reranking Platform

## Goal

Improve ranking quality.

---

## Providers

### MVP

- Voyage AI Reranker

### Future

- CrossEncoder
- Cohere
- Jina

---

## Workflow

```
Top 50 Results

↓

Reranker

↓

Top 5 Results
```

---

## Deliverables

- Provider abstraction
- Voyage provider
- CrossEncoder provider
- Reranking service

---

# Phase 3.7 — Context Building Platform

## Goal

Prepare retrieved knowledge for the LLM.

---

## Architectural Decision

Context Compression belongs to the **Context Building Platform**, not the Retrieval Platform.

Retrieval finds knowledge.

Context Building prepares knowledge.

---

## Responsibilities

- Deduplicate chunks
- Remove overlaps
- Context compression
- Token budgeting
- Context ordering
- Citation preparation

---

## Workflow

```
Retrieved Chunks

↓

Deduplicate

↓

Compress

↓

Token Budget

↓

Prompt Context
```

---

## Deliverables

- Context builder
- Compression
- Token budgeting
- Citation preparation

---

# Phase 3.8 — Generation Platform

## Goal

Generate answers from retrieved context.

---

## Responsibilities

- Prompt templates
- Prompt registry
- LLM provider abstraction
- Streaming
- Structured output

---

## Workflow

```
Prompt Context

↓

LLM

↓

Generated Answer
```

---

## Deliverables

- Generation service
- Prompt platform
- Streaming support
- Structured output

---

# Phase 3.9 — Research APIs

This is the first stage where ResearchMind becomes useful to end users.

---

## Retrieval API

```
POST /retrieve
```

Returns retrieved chunks.

Useful for debugging and evaluation.

---

## Research API

```
POST /research
```

Workflow

```
Question

↓

Retrieval

↓

Context Builder

↓

LLM

↓

Answer
```

---

## Streaming API

```
POST /research/stream
```

Streams tokens as they are generated.

---

## Citation API

```
POST /research/citations
```

Returns

- Answer
- Citations
- Source metadata

---

# Phase 3.10 — Evaluation Platform

## Goal

Measure AI quality continuously.

---

## Offline Evaluation

- Golden datasets
- Retrieval benchmarks
- Embedding comparison
- Chunk evaluation
- Reranker benchmarks

---

## Metrics

### Retrieval

- Recall@K
- Precision@K
- MRR
- NDCG

### Runtime

- Latency
- Cost

### Generation

- Faithfulness
- Groundedness
- Hallucination detection
- Citation accuracy

---

# Future Platforms

---

# Research Platform

User-facing research workspace.

Features

- Research Sessions
- Conversations
- Memory
- Notebooks
- Projects
- Knowledge Bases

---

# AI Platform

Production AI runtime.

Features

- RAG
- LangGraph
- Agents
- Tool Calling
- Memory

---

# MCP Platform

External integrations.

Examples

- Research Papers
- NASA
- GitHub
- Climate
- Earthquake
- Domain-specific MCP servers

---

# Production Platform

Production readiness.

Features

- Deployment
- Monitoring
- Scaling
- Security
- Performance

---

# Final MVP Pipeline

```
                    User Query
                         │
          ┌──────────────┴──────────────┐
          │                             │
     Sparse Search               Dense Search
          │                             │
       Top 50                        Top 50
          └──────────────┬──────────────┘
                         │
                  Reciprocal Rank Fusion
                         │
                     Top 20 Results
                         │
                     Voyage Reranker
                         │
                      Top 5 Results
                         │
                  Context Builder
                         │
                  Context Compression
                         │
                         LLM
                         │
                    Final Answer
                    + Citations
```

---

# MVP Implementation Order

| Milestone | Platform | Deliverables |
|------------|----------|--------------|
| 3.1 | Retrieval Foundation | Query processing, dense retrieval, `/retrieve` |
| 3.2 | Sparse Retrieval | SPLADE query vectors, sparse search |
| 3.3 | Hybrid Retrieval | Dense + Sparse + RRF |
| 3.4 | Retrieval Strategies | Parent/Child, Parallel Retrieval, Query Decomposition |
| 3.5 | Result Processing | Metadata filtering, Top-K |
| 3.6 | Reranking Platform | Voyage AI, CrossEncoder |
| 3.7 | Context Building Platform | Deduplication, Compression, Token Budgeting |
| 3.8 | Generation Platform | Prompting, LLM Runtime, Streaming |
| 3.9 | Research APIs | `/retrieve`, `/research`, `/research/stream`, `/research/citations` |
| 3.10 | Evaluation Platform | Retrieval benchmarks, Hallucination testing, Latency, Cost |

---

# Architecture Principles

- Retrieval is responsible only for finding knowledge.
- Reranking improves ordering.
- Context Building prepares knowledge for the LLM.
- Generation owns all LLM interactions.
- Evaluation measures every AI improvement.
- Every platform is independently testable and replaceable.
- Provider SDKs never leak outside provider implementations.
