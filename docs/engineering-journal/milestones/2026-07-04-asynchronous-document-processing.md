Engineering Journal — Asynchronous Document Processing
Overview

This milestone migrated ResearchMind from a synchronous document processing pipeline to a fully asynchronous architecture using a pluggable queue abstraction.

Previously, uploading a document immediately triggered parsing, metadata extraction, statistics generation, and artifact creation within the HTTP request lifecycle.

After this change, uploads return immediately while background workers perform processing asynchronously.

Motivation

The previous architecture had several limitations:

Long-running HTTP requests
Upload latency proportional to document size
Difficult horizontal scaling
No retry capability
No dead-letter handling
No independent worker scaling

Moving processing to background workers enables production-grade scalability and reliability.

Major Components Added
Duplicate Detection

Added duplicate detection based on SHA-256 checksum.

upload/
└── duplicate/

Features:

SHA-256 hashing
Repository lookup
Conflict detection
Duplicate response models
Dedicated service layer
Statistics Extraction

Introduced a new statistics enrichment pipeline.

processing/
└── statistics/

Components:

interfaces.py
base.py
registry.py
service.py
providers/pdf.py

Current statistics:

Page count
Heading count
Paragraph count
Table count
Figure count
Code block count
List count
References
Character count
Word count
Line count
Queue Infrastructure

Introduced a provider-based queue abstraction.

infrastructure/
└── queue/

Contains:

interfaces.py
factory.py
models.py
exceptions.py

providers/
    valkey.py
    sqs.py
Processing Job Model

Added a transport object representing work sent to background workers.

ProcessingJob

Contains:

document_id
owner_id
storage_key
attempt
created_at
Job Builder

Added:

upload/job_builder.py

Responsible for converting persisted documents into ProcessingJob instances.

Background Worker

Introduced a dedicated processing worker.

apps/worker/

Components:

processing_worker.py
main.py

Responsibilities:

Poll queue
Deserialize jobs
Invoke queued processing
Acknowledge completed jobs
Reject failed jobs
Queued Processing Service

Added:

QueuedDocumentProcessingService

Responsibilities:

Load document
Build ParseRequest
Delegate to DocumentProcessingService
Dependency Injection Changes

Added factory methods for:

Queue provider
Job builder
Queued processing service
Worker
Shared Database Infrastructure

Refactored database initialization.

Before:

FastAPI
    ↓
app.state.postgres_engine

Worker maintained its own engine.

After:

db/session.py

engine

SessionFactory

get_db()

Both API and worker now reuse the same engine and session factory.

Upload Flow

Old flow

Upload

↓

UploadService

↓

ProcessingService

↓

Artifacts

New flow

Upload

↓

UploadService

↓

Persist

↓

Enqueue

↓

HTTP 201
Worker Flow
Worker

↓

Queue

↓

QueuedDocumentProcessingService

↓

DocumentProcessingService

↓

ProcessingService

↓

Artifacts
Important Bug Discovered

During testing, processing artifacts were still generated even when the worker was stopped.

Root cause:

The upload endpoint still invoked:

DocumentProcessingService.process(...)

after enqueueing.

As a result, both synchronous and asynchronous processing were executing.

Resolution:

Removed the synchronous processing invocation from the upload endpoint.

After removal:

Upload only enqueues
Worker performs all processing
Validation Performed

Verified:

✅ Upload succeeds

✅ Document stored

✅ Queue message created

✅ Worker stopped → no artifacts generated

✅ Worker started → artifacts generated

✅ Processing lifecycle

PENDING

↓

PROCESSING

↓

COMPLETED
Outcome

ResearchMind now has a production-ready asynchronous document ingestion pipeline with a pluggable queue abstraction supporting both Valkey and Amazon SQS.
