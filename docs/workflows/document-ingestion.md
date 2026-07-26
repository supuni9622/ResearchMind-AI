# Document Ingestion Workflow

**Status:** Implemented — asynchronous, queue-based.

---

## Flow

```
POST /documents/upload
  │
  ▼
UploadService.upload()          → stores original file, persists document metadata
  │
  ▼
ProcessingQueue.enqueue()       → async job enqueued, request returns immediately (201)
  │
  ▼
ProcessingWorker.run()          → apps/worker/processing_worker.py, continuous poll loop
  │
  ▼
QueuedDocumentProcessingService → dequeues job, invokes ProcessingService.process()
  │
  ▼
ProcessingService.process()     → app/ai/knowledge/processing/service.py
```

## `ProcessingService.process()` stages

| Stage | What happens |
|---|---|
| Download | Fetch uploaded bytes from storage |
| Parse | Format-specific parser (`parsers/docling.py`) → `ProcessedDocument` |
| Metadata enrichment | `metadata/service.py` — per-format providers (`metadata/providers/pdf.py`, `language.py`) |
| Statistics enrichment | `statistics/service.py` — char/word counts, per-format providers |
| Persist processing artifacts | Original + enriched document artifacts written |
| Chunking | `ChunkingStrategy.MARKDOWN` → chunk artifact persisted |
| Embedding | Voyage AI (`EmbeddingProvider.VOYAGE_AI`) |
| Indexing | Qdrant, via `IndexingRequest` |

Every stage is timed via `RuntimeMetricsCollector` (the same collector `benchmarks/pipeline/pipeline_runner.py` reuses for benchmarking — see `docs/workflows/evaluation-pipeline.md`).

## Failure behavior

Upload failures fail the request. Processing failures do **not** fail the upload — they're recorded on the document's processing status; the worker rejects the job rather than crashing.

## Formats supported

PDF, DOCX, Markdown, TXT (per `ADR-010-document-processing-strategy.md`), parsed via Docling.

## Related endpoints

| Endpoint | Purpose |
|---|---|
| `POST /documents/upload` | Upload + enqueue |
| `GET /documents` | List (paginated) |
| `GET /documents/stats` | Owner-scoped indexed-chunk/embedding counts (Qdrant) |
