# Vector Indexing Idempotency Gap

## Source

This gap was identified through feedback on the public architecture discussion
for ResearchMind's asynchronous document-ingestion pipeline.

The comment highlighted that worker idempotency is not limited to retrying a
queue message safely. A retry must also avoid creating duplicate vectors when
an embedding or indexing attempt fails after making partial progress.

## Comment suggestion

Design vector indexing as an idempotent upsert from the beginning. Reprocessing
the same document and chunks should replace the corresponding vector points
instead of inserting additional points.

## Current implementation vs. suggested behavior

| Area | What ResearchMind has now | What the comment suggests | Gap |
|---|---|---|---|
| Queue processing | Failed document jobs are retried by the processing worker and moved to the dead-letter path after the configured attempt limit. | Retain retry behavior, but make every side effect safe to repeat. | Queue retries exist, but a retry can repeat vector-indexing side effects. |
| Vector write operation | Qdrant writes use `upsert`, so a point is replaced when the incoming point ID matches an existing point ID. | Continue using upsert with a stable point ID for each logical document chunk. | Upsert alone is not sufficient when IDs change between attempts. |
| Point identity | A Qdrant point uses the embedding ID. Embedding IDs are generated with `uuid4()` for each execution. | Generate the same point ID whenever the same logical chunk is processed. | A retry can create a new embedding ID and therefore a new Qdrant point. |
| Chunk identity | Chunk IDs are also generated with `uuid4()` during processing. | Base point identity on stable inputs such as document ID, chunk position or locator, chunking configuration, and an optional content fingerprint. | Deriving a point ID only from the current random chunk ID would not make retries deterministic. |
| Document ownership | Every vector payload includes `document_id`, and the vector-store abstraction can delete all points belonging to a document. | Preserve `document_id` for filtering, cleanup, and observability; do not use it as the only point ID because a document contains multiple chunks. | The payload supports document-level cleanup, but it does not prevent duplicates by itself. |
| Reindexing | The explicit `reindex()` flow deletes the document's existing vectors before indexing it again. | Make normal retry behavior idempotent as well, preferably without exposing a delete-then-insert consistency window. | The standard ingestion pipeline calls `index()` rather than `reindex()`. |
| Partial batch failure | Qdrant upserts vectors in batches. Earlier batches may succeed before a later batch fails. | Retrying the same batches should overwrite the same logical points. | Random point IDs can leave successful vectors from the first attempt alongside vectors from the retry. |

## Recommended direction

1. Define a deterministic point-ID scheme for each logical chunk. A suitable
   UUIDv5 input could include:

   - owner ID;
   - document ID;
   - chunking strategy and configuration fingerprint;
   - a stable chunk locator or index; and
   - optionally, a normalized-content fingerprint.

2. Keep `document_id` in the Qdrant payload for filtering and document-level
   deletion.

3. Add a test that simulates a partial indexing failure, retries the document,
   and verifies that the final collection contains one point per logical chunk.

4. Define how stale points are removed when a document is intentionally
   reprocessed with changed content or a different chunking configuration.

## Acceptance criteria

- Repeating the same ingestion job does not increase the number of vector
  points.
- A partial indexing failure followed by a retry produces the same final vector
  state as one successful attempt.
- Reprocessing changed content replaces or removes stale points according to an
  explicit versioning policy.
- Retrieval continues to enforce owner and document metadata filters.

## Relevant implementation locations

- `apps/worker/processing_worker.py`
- `apps/api/app/services/queued_document_processing_service.py`
- `apps/api/app/ai/knowledge/processing/service.py`
- `apps/api/app/ai/knowledge/indexing/service.py`
- `apps/api/app/ai/knowledge/embeddings/factory.py`
- `apps/api/app/ai/knowledge/chunking/chunk_factory.py`
- `apps/api/app/ai/knowledge/vectorstores/providers/qdrant.py`
