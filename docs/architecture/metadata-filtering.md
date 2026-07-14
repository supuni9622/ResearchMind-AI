# Metadata Filtering Architecture

**Status:** 🚧 In Progress
**Phase:** Milestone 2.7.1 — Retrieval Platform
**Last Updated:** 2026-07-14

---

# Purpose

Metadata filtering allows retrieval operations to constrain search results
to a subset of indexed knowledge.

This capability is required for:

- multi-user isolation
- document-scoped search
- future research sessions
- workspaces
- organizations
- authorization boundaries
- improved retrieval precision

Metadata filtering is implemented at the vector database layer using
Qdrant payload filtering.

---

# Architectural Principles

## Provider Independence

Retrieval services remain independent from Qdrant-specific filter
implementations.

The Retrieval Platform communicates only through canonical models.

Provider-specific filter translation happens inside the provider layer.

---

## Evaluation Driven Development

Metadata filtering is treated as a retrieval quality improvement.

Future evaluations should compare:

```text
Unfiltered Retrieval
↓

Metadata Constrained Retrieval
```

Metrics:

- Recall
- Precision
- MRR
- Latency

---

# High Level Workflow

```text
User Question
       │
       ▼
RetrievalQuery
       │
       ▼
Metadata Filters
       │
       ▼
Qdrant Filter Builder
       │
       ▼
Dense / Sparse Search
       │
       ▼
Retrieved Chunks
```

---

# Retrieval Flow

```text
Question
       │
       ▼
Query Embedding
       │
       ▼
Metadata Filter Construction
       │
       ▼
Qdrant Search
       │
       ▼
Top-K Results
```

---

# Supported Filters (v1)

The initial implementation intentionally remains small.

## owner_id

Restrict retrieval to documents belonging to a specific user.

Example:

```json
{
  "filters": {
    "owner_id": "user_123"
  }
}
```

---

## document_id

Restrict retrieval to a single document.

Example:

```json
{
  "filters": {
    "document_id": "uuid"
  }
}
```

---

## filename

Restrict retrieval to a specific uploaded file.

Example:

```json
{
  "filters": {
    "filename": "research.pdf"
  }
}
```

---

# Future Filters

Planned future metadata:

```text
language
tags
workspace_id
organization_id
research_session_id
created_at
updated_at
document_type
```

These fields will be added incrementally as the platform evolves.

---

# Canonical Retrieval Model

```python
class RetrievalQuery(BaseModel):

    query: str

    top_k: int = 5

    filters: dict[str, Any] = Field(
        default_factory=dict,
    )
```

The Retrieval Platform intentionally keeps filtering simple.

Complex boolean filtering and query ASTs are intentionally deferred.

---

# Qdrant Integration

Metadata filtering is translated into Qdrant payload filters.

Example:

```python
Filter(
    must=[
        FieldCondition(
            key="owner_id",
            match=MatchValue(
                value="user_123",
            ),
        ),
    ],
)
```

---

# Dense Retrieval Workflow

```text
Question
      │
      ▼
Query Embedding
      │
      ▼
Qdrant Dense Search
      │
      ▼
Payload Filters Applied
      │
      ▼
Retrieved Chunks
```

---

# Sparse Retrieval Workflow

```text
Question
      │
      ▼
Sparse Query Embedding
      │
      ▼
Qdrant Sparse Search
      │
      ▼
Payload Filters Applied
      │
      ▼
Retrieved Chunks
```

---

# Hybrid Retrieval Workflow

```text
Question
      │
      ▼
Dense Search
      +
Sparse Search
      │
      ▼
Metadata Filtering
      │
      ▼
Reciprocal Rank Fusion
      │
      ▼
Top Results
```

---

# Indexed Payload

Each indexed chunk stores metadata alongside vectors.

```json
{
  "document_id": "...",
  "chunk_id": "...",
  "filename": "...",
  "owner_id": "...",
  "chunk_index": 0,
  "language": null,
  "additional_metadata": {
    "embedding_provider": "voyage_ai",
    "embedding_model": "voyage-3-lite",
    "chunking_strategy": "markdown",
    "parser": "docling"
  }
}
```

---

# API Examples

## Retrieve By Owner

```json
{
  "query": "machine learning",
  "top_k": 5,
  "filters": {
    "owner_id": "user_123"
  }
}
```

---

## Retrieve By Document

```json
{
  "query": "transformers",
  "filters": {
    "document_id": "uuid"
  }
}
```

---

## Retrieve By Filename

```json
{
  "query": "earthquakes",
  "filters": {
    "filename": "earthquake_research.pdf"
  }
}
```

---

# Benefits

Metadata filtering improves:

## Retrieval Precision

Reduce irrelevant chunks.

---

## Multi-Tenancy

Supports future:

```text
Organizations
Workspaces
Research Sessions
```

---

## Authorization

Ensures users only retrieve documents they own.

---

## Future Agent Systems

Agents can search:

```text
specific sessions
specific projects
specific workspaces
```

without polluting retrieval results.

---

# Limitations (v1)

Current limitations:

```text
No OR filtering
No nested filtering
No date filtering
No range filtering
No tags
No language filtering
```

These capabilities may be added after Retrieval Platform stabilization.

---

# Future Evolution

## Metadata Filtering v2

Planned additions:

```text
tags
language
research_session_id
workspace_id
organization_id
```

---

## Metadata Filtering v3

Potential future support:

```text
AND / OR groups
date ranges
hierarchical filters
semantic filters
policy filters
authorization filters
```

---

# Architectural Decision

Metadata filtering is intentionally implemented:

```text
Application Query
        ↓
Canonical Filters
        ↓
Provider Translation
        ↓
Qdrant Payload Filters
```

instead of exposing Qdrant filter models directly.

This preserves:

- provider independence
- future portability
- clean architecture boundaries

---

# Status

```text
Milestone 2.7.1

Metadata Filtering

Status:

🚧 In Progress
```

Exit Criteria:

- Dense retrieval filtering
- Sparse retrieval filtering
- Hybrid retrieval filtering
- API support
- Tests
- Documentation
- Benchmark validation (`benchmarks/retrieval/metadata_filtering_benchmark.py`,
  run via `uv run python -m benchmarks.runner metadatafiltering --dataset
  benchmarks/datasets/research-papers`)
