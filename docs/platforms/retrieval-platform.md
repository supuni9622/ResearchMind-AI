# Retrieval Platform

**Status:** Planned

**Version:** 1.0

---

# Purpose

The Retrieval Platform is responsible for finding the most relevant knowledge from the available indexes.

It acts as the intelligence layer between the Indexing Platform and the AI Runtime.

The platform determines **how** knowledge is retrieved, ranked, filtered, and prepared before it is sent to the LLM.

---

# Goals

The Retrieval Platform exists to:

- Retrieve relevant knowledge
- Support multiple retrieval engines
- Support multiple retrieval strategies
- Combine search results
- Improve retrieval quality
- Prepare context for LLMs
- Evaluate retrieval performance

---

# Non-Goals

The Retrieval Platform does NOT:

- Generate embeddings
- Create indexes
- Manage vector collections
- Generate LLM responses
- Execute AI agents

Those responsibilities belong to other platforms.

---

# Position in the AI Pipeline

```
User Query
      │
      ▼
Query Processing
      │
      ▼
Retrieval Platform
      │
      ▼
Reranking Platform
      │
      ▼
Prompt Builder
      │
      ▼
LLM
```

---

# Platform Architecture

```
                    User Query
                         │
                         ▼
                 Query Processing
                         │
                 Retrieval Strategy
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 Semantic Search                    Keyword Search
 (Vector Index)                      (BM25 Index)
        └────────────────┬────────────────┘
                         ▼
                   Result Fusion
                         ▼
                Metadata Filtering
                         ▼
                   Voyage Reranker
                         ▼
                     Top-K Results
                         ▼
                  Context Builder
                         ▼
                        LLM
```

---

# Responsibilities

The Retrieval Platform owns:

- Query processing
- Search execution
- Retrieval strategies
- Search orchestration
- Result fusion
- Metadata filtering
- Retrieval caching
- Retrieval evaluation

---

# Platform Components

## 1. Query Processing

Purpose

Prepare the user's query before searching.

Responsibilities

- Query normalization
- Query cleaning
- Query decomposition
- Future query expansion

Output

Canonical search query.

---

## 2. Search Engines

Search engines retrieve candidate documents.

The MVP includes two search engines.

### Semantic Search

Uses

- Voyage embeddings
- Qdrant

Best for

- Semantic similarity
- Concept matching
- Natural language queries

---

### Keyword Search

Uses

- BM25

Best for

- Exact matching
- Technical identifiers
- Error messages
- RFC numbers
- API names
- Version numbers

---

### Hybrid Search

Combines

- Semantic Search
- Keyword Search

Hybrid Search is the default retrieval engine for ResearchMind.

---

# Retrieval Strategies

Search engines determine **where** to search.

Retrieval strategies determine **how** to search.

---

## Strategy 1

### Standard Retrieval

```
Query

↓

Hybrid Search

↓

Rerank

↓

Top-K
```

Baseline retrieval strategy.

---

## Strategy 2

### Parent / Child Retrieval

Purpose

Retrieve using small chunks while returning larger parent context.

Workflow

```
Query

↓

Child Search

↓

Parent Expansion

↓

Rerank
```

Benefits

- Better retrieval precision
- Better context preservation

Recommended for

- Documentation
- Books
- Research papers

---

## Strategy 3

### Query Decomposition

Purpose

Split complex questions into smaller queries.

Workflow

```
Complex Query

↓

Planner

↓

Sub Queries

↓

Hybrid Search

↓

Merge

↓

Rerank
```

Benefits

- Better evidence collection
- Improved research quality

Recommended for

- Comparative questions
- Multi-topic questions
- Research workflows

---

# Result Processing

Candidate results are refined before being sent to the LLM.

---

## Result Fusion

Purpose

Merge results from multiple search engines.

Initial implementation

- Reciprocal Rank Fusion (RRF)

Future

Additional fusion algorithms.

---

## Metadata Filtering

Support filtering by

- owner_id
- workspace_id
- document_id
- filename
- language
- tags
- source

Purpose

Improve precision and support scoped retrieval.

---

## Reranking

Provider

Voyage AI

Purpose

Reorder retrieved candidates according to relevance.

Pipeline

```
Retrieved Results

↓

Voyage Reranker

↓

Top-K Results
```

---

## Top-K Selection

Purpose

Select the optimal context size for the LLM.

Future

Adaptive Top-K selection.

---

# Context Builder

Responsibilities

- Merge retrieved chunks
- Preserve metadata
- Preserve citations
- Prepare LLM context

Output

Canonical retrieval context.

---

# Caching

The Retrieval Platform owns retrieval caching.

---

## Retrieval Cache

Purpose

Reuse search results for repeated queries.

Benefits

- Lower latency
- Lower infrastructure cost
- Better user experience

---

Future

- Semantic cache
- Query cache

---

# Evaluation

Every retrieval strategy must be measurable.

Metrics

- Recall@K
- Precision@K
- MRR
- NDCG
- Latency
- Cost

Evaluation supports:

- Benchmarking
- Regression testing
- Strategy comparison

---

# Folder Structure

```
retrieval/

    models.py

    enums.py

    interfaces.py

    exceptions.py

    service.py

    strategies/

        standard.py

        hybrid.py

        parent_child.py

        query_decomposition.py

    search/

        semantic.py

        keyword.py

        hybrid.py

    processing/

        fusion.py

        metadata_filter.py

        reranker.py

        context_builder.py

    cache/

        service.py

    evaluation/

        metrics.py

        benchmark.py

    artifacts/

        models.py

        builder.py

        writer.py
```

---

# Canonical Workflow

```
User Query
      │
      ▼
Query Processing
      │
      ▼
Select Strategy
      │
      ▼
Execute Search
      │
      ▼
Result Fusion
      │
      ▼
Metadata Filtering
      │
      ▼
Reranking
      │
      ▼
Top-K Selection
      │
      ▼
Context Builder
      │
      ▼
Retrieval Artifact
```

---

# MVP Scope

## Search Engines

- Semantic Search
- BM25 Search
- Hybrid Search

---

## Retrieval Strategies

- Standard Retrieval
- Parent / Child Retrieval
- Query Decomposition

---

## Result Processing

- Result Fusion
- Metadata Filtering
- Voyage Reranking
- Top-K Selection

---

## Performance

- Retrieval Cache

---

## Evaluation

- Recall@K
- Precision@K
- MRR
- NDCG
- Latency
- Cost

---

# Deferred Features

The following capabilities are intentionally postponed:

- Knowledge Graph Retrieval
- GraphRAG
- Multi-hop Retrieval
- Agentic Retrieval
- Adaptive Strategy Selection
- Learning-to-Rank
- Self-improving Retrieval

---

# Design Principles

## Retrieval is Independent

Retrieval never creates indexes.

---

## Strategy Driven

Search behavior is defined by retrieval strategies.

---

## Engine Agnostic

Search engines are interchangeable.

---

## Provider Independent

External SDKs never leak into business logic.

---

## Evaluation First

Every retrieval improvement must be measurable.

---

## Production Ready

Every component should support:

- Reliability
- Scalability
- Observability
- Cost efficiency

---

# Relationship to Other Platforms

```
Indexing Platform

        │

        ▼

Retrieval Platform

        │

        ▼

Reranking Platform

        │

        ▼

AI Runtime
```

The Retrieval Platform consumes searchable knowledge from the Indexing Platform and produces optimized context for the AI Runtime.

It is the intelligence layer responsible for selecting the best knowledge available for answering user queries.
