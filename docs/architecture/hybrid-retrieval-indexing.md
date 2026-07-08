# Hybrid Retrieval Indexing — Sparse Embeddings & the Complete Ingestion Pipeline

**Project:** ResearchMind AI
**Platform:** Knowledge Platform → Indexing Platform
**Phase:** 2.5 — Qdrant Native Hybrid Retrieval
**Status:** ✅ Completed (V1) — Indexing side. Retrieval/query side is future work.
**Last Updated:** 2026-07-08
**Related ADRs:** [ADR-018](../adrs/ADR-018-knowledge-indexing-and-retrieval-architecture.md), [ADR-019](../adrs/ADR-019-qdrant-native-hybrid-retrieval.md)

---

# Overview

This document records what was implemented to add **sparse embedding generation and Qdrant native hybrid indexing** to the Indexing Platform, and documents the **complete ingestion pipeline** as it exists after this change.

Before this work, the pipeline generated only dense vectors (Voyage AI) and indexed them into Qdrant as a single unnamed vector per point. This is sufficient for semantic search but weak for exact lexical matches — RFC numbers, error codes, API names, function names, version numbers — the kind of tokens research documents are full of.

Per [ADR-019](../adrs/ADR-019-qdrant-native-hybrid-retrieval.md), ResearchMind does **not** stand up a separate BM25 platform for this. Instead, every chunk now also gets a **sparse SPLADE vector** (FastEmbed), and both vectors are written into the **same Qdrant point** so Qdrant can serve semantic search, sparse/lexical search, and hybrid fusion from one collection.

---

# What Changed

- Added `FastEmbedSparseEmbeddingProvider` (`indexing/providers/fastembed.py`) — generates SPLADE sparse vectors from chunk text using the `fastembed` library, off the event loop.
- `IndexingService` now builds a sparse vector for every chunk alongside its dense embedding and upserts both together.
- `IndexingRequest` gained a `chunk_artifact` field — sparse generation needs the raw chunk text, which `EmbeddingArtifact` does not retain.
- Qdrant collections now use **named vectors** (`dense` + `sparse`) instead of a single unnamed vector — this is a schema change, required by Qdrant to store more than one vector type per point.
- New canonical model `SparseVector` (`indices` + `values`), attached to `VectorStoreRecord.sparse_vector`.
- `IndexStatistics` gained `indexed_sparse_vectors` for observability.
- New setting `sparse_embedding_model` (default `prithivida/Splade_PP_en_v1`).
- New dependency: `fastembed`.
- Fixed a latent bug in the same code path: `VectorPayload.chunk_index` was hardcoded to `0` for every chunk; it now uses the chunk's real position.

No folder structure changed. Everything landed inside the already-scaffolded `indexing/` platform (`indexing/providers/fastembed.py` existed as an empty stub before this work).

---

# Complete Ingestion Pipeline

This is the full flow from document upload to a point being searchable in Qdrant.

```text
Upload
  │
  ▼
UploadService
  │
  ▼
ProcessingQueue
  │
  ▼
ProcessingWorker
  │
  ▼
ProcessingService.process()
  │
  ├──▶ 1. Download from S3
  │
  ├──▶ 2. Parse            (DoclingParser)               → ProcessedDocument
  │
  ├──▶ 3. Enrich Metadata  (PDF, Language providers)
  │
  ├──▶ 4. Enrich Statistics(PDF statistics provider)
  │
  ├──▶ 5. Persist Processing Artifacts (markdown, text, blocks)
  │
  ├──▶ 6. Chunking Stage   (ChunkingService, MARKDOWN strategy) → ChunkArtifact
  │         │
  │         └──▶ persist chunks.json
  │
  ├──▶ 7. Embedding Stage  (EmbeddingService, Voyage AI)        → EmbeddingArtifact
  │         │
  │         └──▶ persist embeddings.json
  │
  ├──▶ 8. Indexing Stage   (IndexingService)                    → IndexingArtifact
  │         │
  │         ├──▶ 8a. Generate sparse vectors  (FastEmbed SPLADE, per chunk text)
  │         ├──▶ 8b. Build VectorStoreRecord[] (dense + sparse + payload)
  │         ├──▶ 8c. Create Qdrant collection if missing (named dense+sparse vectors)
  │         ├──▶ 8d. Upsert points into Qdrant
  │         └──▶ persist indexing.json
  │
  ▼
Knowledge Ready
```

Every stage consumes the canonical artifact produced by the previous stage. No stage reaches back into an earlier stage's internals.

---

# Indexing Stage — Detailed Sequence

This is what `IndexingService.index()` does, step by step, after this change.

```text
IndexingRequest
(owner_id, embedding_artifact, chunk_artifact)
        │
        ▼
Validate
  - embedding_artifact.embeddings not empty
  - chunk_artifact.chunks not empty
        │
        ▼
Build CollectionDefinition
  - name, dimensions, distance metric
  - taken from embedding_artifact.statistics / execution
        │
        ▼
Build Vector Records
        │
        ├──▶ Match each Embedding to its source Chunk by chunk_id
        │
        ├──▶ FastEmbedSparseEmbeddingProvider.embed(
        │        [chunk.content.text for every embedded chunk]
        │    )
        │        │
        │        ▼
        │    SparseVector[]  (indices + values, one per chunk)
        │
        └──▶ VectorStoreRecord(
                 id            = embedding.id
                 vector        = embedding.vector.values      (dense)
                 sparse_vector = SparseVector                 (sparse)
                 payload       = document_id, chunk_id, filename,
                                 owner_id, chunk_index, ...
             )
        │
        ▼
collection_exists? ──No──▶ create_collection()
        │                    - vectors_config:        { "dense":  VectorParams }
        │                    - sparse_vectors_config:  { "sparse": SparseVectorParams }
        │ Yes
        ▼
upsert(records)
        │
        ▼
Build IndexStatistics
  - indexed_vectors, indexed_sparse_vectors, duration_ms
        │
        ▼
Build + persist IndexingArtifact  → indexing.json
        │
        ▼
IndexingResult
```

---

# Qdrant Collection Schema

## Before this change

A single unnamed dense vector per point:

```json
{
  "vectors": {
    "size": 512,
    "distance": "Dot"
  }
}
```

## After this change

Named dense + sparse vectors on the same point:

```json
{
  "vectors": {
    "dense": { "size": 512, "distance": "Dot" }
  },
  "sparse_vectors": {
    "sparse": { "index": { "on_disk": false } }
  }
}
```

This is a **breaking schema change** — Qdrant cannot migrate an existing collection from an unnamed vector to named vectors in place. Any pre-existing `researchmind_knowledge` collection created before this change must be dropped and recreated (`IndexingService` will recreate it automatically the next time it does not find an existing collection). The dev collection was migrated this way as part of implementing and verifying this feature.

---

# Canonical Model Changes

```text
VectorStoreRecord
├── id
├── vector             (dense, unchanged)
├── sparse_vector       ← NEW: SparseVector | None
└── payload

SparseVector            ← NEW
├── indices: list[int]
└── values: list[float]

IndexStatistics
├── indexed_vectors
├── indexed_sparse_vectors  ← NEW
├── failed_vectors
├── batch_size
└── duration_ms

IndexingRequest
├── owner_id
├── operation
├── embedding_artifact
└── chunk_artifact      ← NEW (sparse generation needs raw chunk text)
```

No existing field was removed or renamed. `sparse_vector` defaults to `None` and `indexed_sparse_vectors` defaults to `0`, so previously-written artifacts remain valid to deserialize.

---

# Storage Layout

Artifacts produced by ingestion, per document:

```text
documents/
    {owner_id}/
        {document_id}/
            parsed.md
            parsed.txt
            processed_document.json

            chunking/
                {strategy}/
                    {artifact_id}/
                        chunks.json

            embeddings/
                {provider}/
                    {artifact_id}/
                        embeddings.json

            indexing/
                {execution_id}/
                    indexing.json
```

Vector data itself lives in Qdrant, not S3 — only the indexing execution's metadata (collection, statistics, execution status) is written to `indexing.json`.

---

# Component Responsibilities

## FastEmbedSparseEmbeddingProvider

Responsibilities

- Load the SPLADE ONNX model (`prithivida/Splade_PP_en_v1` by default)
- Generate sparse vectors from raw chunk text
- Run inference on a worker thread (`asyncio.to_thread`) since FastEmbed is synchronous and CPU-bound
- Wrap FastEmbed failures in `SparseEmbeddingError`

Does NOT

- Know about Qdrant, chunks, or embedding artifacts
- Persist anything
- Expose FastEmbed SDK types outside the provider

This provider is intentionally **not** a peer of the dense `EmbeddingProvider` implementations (Voyage, OpenAI, Sentence Transformers). Sparse vector generation isn't a swappable, user-facing embedding choice — it exists purely to feed Qdrant's native hybrid index, so it is owned by the Indexing Platform rather than the Embedding Platform.

---

## IndexingService (updated)

Responsibilities

- Orchestrate indexing: validate → build records (dense + sparse) → create collection if missing → upsert → build statistics → persist artifact
- Match each dense embedding back to its source chunk by `chunk_id` to retrieve the text sparse generation needs

Does NOT

- Generate dense embeddings
- Know FastEmbed or Qdrant SDK types (both stay behind their provider abstractions)

---

## QdrantVectorStoreProvider (updated)

Responsibilities

- Create collections with named `dense` + `sparse` vector configs
- Convert `VectorStoreRecord` into a Qdrant `PointStruct` carrying both named vectors
- Read collection metadata back out of the named `dense` vector config

Does NOT

- Decide whether a sparse vector should exist for a record (that's the caller's responsibility — the provider just attaches whatever is present)

---

# Verification

This was verified against real infrastructure, not just unit tests:

1. Inspected the running dev Qdrant instance — found an existing `researchmind_knowledge` collection with 1,958 points on the old single-vector schema (from prior benchmark runs).
2. Dropped and let it be recreated with the new named dense+sparse schema.
3. Ran the real pipeline (real Voyage AI dense embeddings + real FastEmbed SPLADE sparse embeddings + real Qdrant) end-to-end through `IndexingService`, producing a collection with:
   ```json
   "vectors": { "dense": { "size": 512, "distance": "Dot" } },
   "sparse_vectors": { "sparse": { "index": { "on_disk": false } } }
   ```
4. Issued a real sparse-vector query for `"What does RFC-7231 define?"` against two indexed chunks (one about Qdrant, one about RFC-7231). The RFC-7231 chunk scored **17.15** vs. **0.66** for the unrelated chunk — confirming sparse/lexical matching correctly favors the keyword-relevant chunk, and that `chunk_index` in the payload is now correct (previously hardcoded to `0`).
5. Cleaned up the smoke-test points afterward, leaving an empty, correctly-shaped collection for real ingestion.
6. Full test suite (234 tests) + `ruff` + `mypy` pass.

---

# Configuration

```text
SPARSE_EMBEDDING_MODEL=prithivida/Splade_PP_en_v1     (new, optional — has a default)
```

New dependency:

```text
fastembed
```

---

# Folder Structure (Indexing Platform)

```text
indexing/
    models.py
    enums.py
    interfaces.py
    exceptions.py
    service.py

    providers/
        fastembed.py        ← implemented in this change

    artifacts/
        models.py
        builder.py
        writer.py
```

---

# Future Roadmap

Indexing now produces both dense and sparse vectors in the same Qdrant collection. What Qdrant does with them at query time is Retrieval Platform work and remains ahead, per ADR-019's ordering:

```text
1. Semantic Retrieval        (dense-only query)

2. Sparse Retrieval          (sparse-only query)

3. Hybrid Retrieval          (Qdrant fusion of dense + sparse)

4. Metadata Filtering

5. Voyage Reranker

6. Parent / Child Retrieval

7. Query Decomposition

8. Retrieval Evaluation
```

None of this exists yet — this document covers only the indexing side. The Retrieval Platform (`retrieval/`) is currently an empty package.

---

# Key Architectural Decisions

- Sparse vector generation is owned by the Indexing Platform, not the Embedding Platform — it isn't a swappable business capability, it exists solely to feed Qdrant hybrid search.
- Dense and sparse vectors are written to the same Qdrant point under named vectors (`dense`, `sparse`), not to separate collections or a separate BM25 system.
- `IndexingRequest` carries the `chunk_artifact` because `EmbeddingArtifact` intentionally does not retain raw text — sparse generation is the first consumer that needs text at indexing time.
- Qdrant collection schema changes (unnamed → named vectors) are not migrated in place; a changed schema means drop-and-recreate, not a data migration path.
- `SparseVector` and the new statistics fields are additive and default-safe, so previously persisted `EmbeddingArtifact`/`IndexingArtifact` JSON remains valid to load.
