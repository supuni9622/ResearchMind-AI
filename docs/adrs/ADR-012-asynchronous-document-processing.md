# ADR-012: Asynchronous Document Processing Architecture

## Status

Accepted

---

## Context

ResearchMind ingests user documents and processes them through a
document intelligence pipeline.

The pipeline currently performs:

- Document parsing
- Metadata extraction
- Statistics enrichment
- Artifact generation

Future phases will extend the pipeline with:

- Chunk generation
- Embedding generation
- Vector indexing
- OCR
- Citation extraction
- Document quality evaluation

During the early implementation stages, document processing was
executed synchronously within the upload request.

This approach was intentionally chosen to validate:

- document parsing
- metadata extraction
- statistics enrichment
- artifact generation
- storage integration
- processing lifecycle
- error handling

before introducing asynchronous infrastructure.

---

## Problem

Executing the entire processing pipeline inside the HTTP request has
several drawbacks.

Long-running requests:

- increase request latency
- consume application workers
- reduce throughput
- make retries difficult
- tightly couple uploads with AI processing

As the platform grows, additional processing stages would further
increase request duration.

---

## Decision

Document uploads and document processing are separated into independent
responsibilities.

The upload request is responsible for:

- validating uploads
- duplicate detection
- storing the original document
- persisting document metadata
- enqueueing a processing job

The upload request does **not** perform document processing.

A dedicated processing worker consumes queued jobs and invokes the
existing document processing pipeline.

```
                Upload API
                     │
                     ▼
             UploadService
                     │
                     ▼
         Persist Document Metadata
                     │
                     ▼
            Processing Queue
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
   Valkey Queue             Amazon SQS
                     │
                     ▼
          Processing Worker
                     │
                     ▼
    DocumentProcessingService
                     │
                     ▼
         ProcessingService
                     │
                     ▼
     Metadata / Statistics /
       Artifact Generation
```

The worker becomes responsible only for execution.

Business logic remains inside the existing application services.

---

## Rationale

Separating execution from business logic provides several benefits.

### Improved User Experience

Uploads complete immediately after persistence rather than waiting for
AI processing.

### Scalability

Multiple processing workers can consume jobs concurrently without
modifying the application layer.

### Reliability

Failures become isolated to processing workers rather than affecting
user uploads.

### Retry Support

Failed jobs can be retried without requiring users to upload the
document again.

### Future Processing Pipeline

Additional processing stages can be introduced without changing the
upload workflow.

Examples include:

- chunk generation
- embedding generation
- vector indexing
- OCR
- quality evaluation

---

## Queue Abstraction

The application depends only on the `ProcessingQueue` abstraction.

Concrete implementations include:

- Valkey
- Amazon SQS

Queue provider selection is configuration-driven.

```
QUEUE_PROVIDER=valkey
```

↓

```
QUEUE_PROVIDER=sqs
```

No application code changes are required.

---

## Responsibilities

### UploadService

Responsible for:

- validation
- duplicate detection
- document persistence
- queue submission

Not responsible for:

- parsing
- metadata extraction
- AI processing

---

### Processing Worker

Responsible for:

- consuming queue messages
- invoking document processing
- acknowledging completed jobs
- rejecting failed jobs

Not responsible for:

- upload validation
- storage
- duplicate detection

---

### DocumentProcessingService

Responsible for:

- processing lifecycle
- status transitions
- failure handling
- persistence of processing state

This service is intentionally reused by the worker.

No business logic is duplicated.

---

### ProcessingService

Responsible for executing the document intelligence pipeline.

Responsibilities include:

- parser selection
- metadata enrichment
- statistics enrichment
- artifact generation

The service remains completely unaware of queues and workers.

---

## Alternatives Considered

### Continue synchronous processing

Rejected.

This does not scale as additional AI processing stages are introduced.

---

### Invoke ProcessingService directly from UploadService

Rejected.

This couples uploads with document processing and prevents independent
scaling.

---

### Move business logic into the worker

Rejected.

Business logic belongs in reusable application services rather than
execution infrastructure.

The worker should orchestrate execution only.

---

## Consequences

### Positive

- clear separation of concerns
- shorter upload requests
- reusable business services
- scalable processing architecture
- provider-independent queue infrastructure
- easier retries
- easier monitoring

### Negative

- additional infrastructure
- asynchronous consistency
- increased operational complexity

---

## Implementation Status

Completed:

- UploadService
- Duplicate Detection
- Queue Abstraction
- Valkey Queue Provider
- Amazon SQS Queue Provider
- Queue Factory
- Processing Job Builder
- Queue Submission

Remaining:

- Processing Worker
- Retry Policy
- Dead Letter Queue
- Worker Observability
- Provider Switching Validation

---

## Future Evolution

The asynchronous architecture becomes the execution platform for all AI
pipelines.

Future queue-based stages include:

```
Upload
    │
    ▼
Processing
    │
    ▼
Chunk Generation
    │
    ▼
Embedding Generation
    │
    ▼
Vector Indexing
    │
    ▼
Knowledge Graph
    │
    ▼
Evaluation
```

Each stage can scale independently while preserving the same
application-layer abstractions.

---

## References

- ADR-009 — Queue Abstraction
- Phase 2.2.6 — Upload Queue & Asynchronous Processing
