# Asynchronous Document Processing

## Overview

ResearchMind processes uploaded documents **asynchronously** using a background worker and a pluggable queue abstraction.

Instead of parsing documents during the HTTP request, the API uploads the file, stores its metadata, places a processing job into a queue, and immediately returns a response to the client. A separate worker consumes queued jobs and performs the computationally expensive processing.

This architecture significantly improves responsiveness, scalability, and reliability while allowing the processing infrastructure to evolve independently of the API.

---

# Why Asynchronous Processing?

Large document processing is inherently slow.

A single document may require:

- Downloading from storage
- Parsing (Docling)
- Metadata extraction
- Statistics generation
- Artifact generation
- Chunking (future)
- Embedding generation (future)
- Vector indexing (future)

Even medium-sized PDFs can take several seconds to process.

If all of this occurs inside an HTTP request:

- Users wait unnecessarily.
- API workers remain occupied.
- Throughput decreases.
- Timeouts become more likely.
- Scaling becomes expensive.

Instead, the upload request should complete as quickly as possible.

---

# Synchronous vs Asynchronous

## Traditional Synchronous Flow

```text
Client
    │
    ▼
Upload API
    │
    ▼
Upload File
    │
    ▼
Parse Document
    │
    ▼
Extract Metadata
    │
    ▼
Generate Artifacts
    │
    ▼
Store Results
    │
    ▼
Return Response
```

Problems:

- Long HTTP requests
- Poor scalability
- Difficult retries
- API blocked during processing
- Risk of request timeout

---

## ResearchMind Asynchronous Flow

```text
Client
    │
    ▼
Upload API
    │
    ▼
Upload Original File
    │
    ▼
Persist Document
    │
    ▼
Create Processing Job
    │
    ▼
Queue
    │
    ▼
HTTP 201 Created
```

The request completes immediately.

Background processing continues independently.

---

# Background Processing

A dedicated worker continuously consumes jobs from the configured queue.

```text
Queue
    │
    ▼
Worker
    │
    ▼
QueuedDocumentProcessingService
    │
    ▼
DocumentProcessingService
    │
    ▼
ProcessingService
    │
    ▼
Artifacts
```

The worker has no dependency on HTTP requests.

It simply processes jobs whenever they become available.

---

# Complete Architecture

```text
                   Upload API
                        │
                        ▼
                 UploadService
                        │
        ┌───────────────┴────────────────┐
        │                                │
        ▼                                ▼
Upload Original PDF              Persist Document
        │                                │
        └───────────────┬────────────────┘
                        ▼
              Build Processing Job
                        │
                        ▼
                 Processing Queue
             (Valkey or Amazon SQS)
                        │
                        ▼
               Processing Worker
                        │
                        ▼
      QueuedDocumentProcessingService
                        │
                        ▼
        DocumentProcessingService
                        │
                        ▼
            ProcessingService
                        │
                        ▼
         Docling + Metadata + Statistics
                        │
                        ▼
               Generated Artifacts
                        │
                        ▼
                    Amazon S3
```

---

# Queue Abstraction

ResearchMind does not depend on a specific queue technology.

Instead, the application depends on the `ProcessingQueue` interface.

```text
ProcessingQueue
        ▲
        │
 ┌──────┴─────────┐
 │                │
 ▼                ▼
ValkeyQueue    SQSQueue
```

This abstraction allows switching queue providers without changing application code.

---

# Queue Providers

## Development

Current development uses:

- Valkey

Advantages:

- Simple setup
- Lightweight
- Fast local development
- Docker friendly

---

## Production

Production uses:

- Amazon SQS

Advantages:

- Fully managed
- Highly available
- Durable
- Infinite horizontal scaling
- Native Dead Letter Queue support

Switching providers requires only configuration.

---

# Processing Job

Instead of sending an entire document through the queue, ResearchMind sends a lightweight job.

```text
ProcessingJob
```

Contains:

- document_id
- owner_id
- storage_key
- attempt
- created_at

The worker retrieves the remaining information directly from the database.

This keeps queue messages small and resilient.

---

# Worker Responsibilities

The worker performs the complete processing pipeline.

1. Receive job
2. Load document from database
3. Download original file from S3
4. Detect document format
5. Parse document
6. Extract metadata
7. Generate statistics
8. Build processing artifacts
9. Upload artifacts
10. Update processing status

---

# Document Lifecycle

Every uploaded document transitions through a well-defined lifecycle.

```text
PENDING
    │
    ▼
PROCESSING
    │
    ▼
COMPLETED
```

If processing fails:

```text
PENDING
    │
    ▼
PROCESSING
    │
    ▼
FAILED
```

This state machine allows users and administrators to track processing progress.

---

# Generated Artifacts

Processing produces several derived files.

Current artifacts:

```text
original.pdf
parsed.md
parsed.txt
processed_document.json
```

Future artifacts may include:

- chunks.json
- embeddings.json
- OCR output
- extracted images
- tables
- semantic indexes

---

# Duplicate Detection

Before a document is queued, ResearchMind computes a SHA-256 checksum.

Workflow:

```text
Upload
    │
    ▼
SHA-256
    │
    ▼
Repository Lookup
    │
    ▼
Duplicate?
```

If an identical document already exists for the same owner, the upload is rejected before unnecessary processing occurs.

---

# Why Use a Queue?

Queues provide several production advantages.

## Decoupling

The API is no longer responsible for expensive processing.

---

## Reliability

Jobs remain in the queue until successfully processed.

---

## Horizontal Scaling

Multiple workers can process documents simultaneously.

```text
Queue
   │
   ├────────► Worker 1
   ├────────► Worker 2
   ├────────► Worker 3
   └────────► Worker N
```

Scaling processing becomes independent of scaling the API.

---

## Retry Support

Transient failures can be retried automatically.

Examples:

- Temporary S3 outage
- Network interruption
- Parser failure
- External API timeout

---

## Dead Letter Queues

Jobs that repeatedly fail can eventually be moved into a Dead Letter Queue (DLQ) for manual investigation.

This prevents problematic documents from blocking the system.

---

# Future Improvements

The asynchronous architecture enables several future capabilities.

## Retry Policies

- Configurable retry count
- Exponential backoff
- Retry metrics

---

## Dead Letter Queue

Failed jobs exceeding retry limits will be moved into a dedicated DLQ.

---

## Priority Queues

High-priority documents may be processed before standard uploads.

---

## Scheduled Processing

Processing jobs may be delayed until a specified time.

---

## Multiple Worker Types

Future workers may specialize in different workloads.

Examples:

- Parsing Worker
- OCR Worker
- Embedding Worker
- Chunking Worker
- AI Enrichment Worker

---

# Design Principles

The asynchronous processing architecture follows several core engineering principles.

- Separation of concerns
- Loose coupling
- Provider abstraction
- Background execution
- Horizontal scalability
- Production-first design
- Cloud-native architecture

---

# Summary

ResearchMind uses asynchronous document processing to separate user-facing uploads from computationally expensive document analysis.

Uploads complete immediately while dedicated background workers process documents independently using a configurable queue backend.

This architecture provides a scalable foundation for future AI capabilities including chunking, embeddings, vector indexing, retrieval pipelines, and agentic workflows.
