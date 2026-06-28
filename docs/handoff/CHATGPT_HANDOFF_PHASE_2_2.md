# ResearchMind AI — Master Project Context & Handoff

**Version:** Phase 2.2 Start
**Project Status:** Phase 2.1 Completed ✅
**Next Milestone:** Phase 2.2 — Document Processing

---

# Project Vision

ResearchMind AI is a production-grade AI research platform built to demonstrate real-world AI Engineering.

The objective is **not** to build another CRUD application or chatbot.

The objective is to engineer a complete production AI platform demonstrating:

* Retrieval-Augmented Generation (RAG)
* Agentic AI
* LangGraph workflows
* Model Context Protocol (MCP)
* AI Evaluation
* AI Observability
* Memory Systems
* Production Deployment
* Enterprise AI Architecture

The project should resemble how modern AI platforms are engineered inside leading technology companies.

---

# Primary Goal

The goal is to become an excellent **AI Engineer / AI Integration Engineer**, not merely a backend engineer.

Backend engineering exists only to support the AI platform.

As implementation progresses, engineering discussions should increasingly focus on AI systems rather than infrastructure.

---

# Collaboration Rules

ChatGPT should act as:

* Senior AI Engineer
* Technical Architect
* Mentor

Responsibilities:

* Always know the current milestone.
* Maintain roadmap traceability.
* Challenge ideas only when there is a strong production reason.
* Avoid unnecessary architecture discussions.
* Avoid over-engineering.
* Build incrementally.
* Freeze decisions once implemented.
* Explain engineering decisions while implementing.

Implementation always takes priority over theoretical improvements.

---

# Implementation Rules

For every implementation:

* Provide complete files.
* Never provide partial snippets.
* Always specify exact file paths.
* Explain where every file belongs.
* Explain why each implementation exists.
* Provide commands to execute.
* Provide verification steps.
* Provide commit messages.

Never use placeholders.

Never leave incomplete implementations.

---

# Engineering Philosophy

ResearchMind follows pragmatic production engineering.

Principles:

* Keep it simple.
* Build vertical slices.
* Avoid premature optimization.
* Separate concerns.
* Prefer composition over complexity.
* Freeze architecture once implemented.
* Refactor only when justified by real requirements.

---

# Core Engineering Principle

**Everything important must be measurable.**

Every feature should eventually define:

* Success metrics
* Operational metrics
* Quality metrics
* Failure metrics

Evaluation and observability are treated as first-class engineering concerns.

---

# Documentation Strategy

Each milestone owns its own documentation.

```
docs/

    ai/

        knowledge-platform/

            milestone/

                README.md
                architecture.md
                implementation.md
                observability.md
                evaluation.md
                runbook.md
                changelog.md
                retrospective.md
                adr.md
```

Documentation supports implementation and remains concise.

---

# Cross-Cutting Engineering Capabilities

These evolve throughout the project instead of being isolated phases.

* Structured Logging
* Metrics
* Distributed Tracing
* AI Evaluation
* Testing
* Security
* Performance
* Cost Tracking
* Engineering Analytics

Every milestone should strengthen these capabilities.

---

# AI Engineering Philosophy

Every AI subsystem should eventually include:

* Architecture
* Implementation
* Testing
* Observability
* Evaluation
* Benchmarking
* Documentation

Whenever multiple AI approaches exist, compare them before implementation.

Evaluation should guide engineering decisions.

---

# Frozen High-Level AI Core

```
AI Core
│
├── Provider Registry
├── Model Router
├── Prompt Registry
├── Embedding Service
├── Retrieval Service
├── Evaluation Service
├── Cost Tracker
├── Token Tracker
├── Model Registry
└── AI Configuration
        │
        ▼
Providers
(Groq,
 OpenRouter,
 OpenAI,
 Anthropic,
 Ollama,
 Future Providers)
```

This architecture is frozen.

---

# AI Technology Stack

## Backend

* Python 3.12
* FastAPI
* SQLAlchemy 2.x
* Alembic
* PostgreSQL
* Valkey
* Structlog
* Pydantic v2

## AI

* LangChain
* LangGraph
* LangSmith (from the beginning)
* Sentence Transformers
* Pydantic AI (comparison / selected use cases)

## Providers

Initially:

* Groq
* OpenRouter

Future:

* OpenAI
* Anthropic
* Ollama
* Gemini
* Azure OpenAI

Provider expansion should not require business logic changes.

## Vector Database

* Qdrant

## Storage

* Amazon S3

## Authentication

* AWS Cognito

## Development

* uv
* Ruff
* MyPy
* Pytest
* Pre-commit

---

# Frozen Architectural Decisions

The following decisions are frozen unless a production requirement justifies change.

## Authentication

AWS Cognito manages identity.

ResearchMind never stores passwords.

Authentication flow:

```
Frontend

↓

AWS Cognito

↓

JWT

↓

ResearchMind API

↓

Current User

↓

Application
```

---

## Document Storage

Binary files:

Amazon S3

Metadata:

PostgreSQL

Never store binary files in PostgreSQL.

---

## Storage Layout

```
documents/

    {owner_id}/

        {document_id}/

            original.pdf
```

Future assets:

```
parsed.md
metadata.json
chunks.json
embeddings.json
preview.png
```

---

## Upload Endpoint

Frozen API

```
POST /api/v1/documents/upload
```

Future APIs

```
GET    /documents

GET    /documents/{id}

DELETE /documents/{id}

POST   /documents/upload

POST   /documents/{id}/reprocess

POST   /documents/{id}/chunk

POST   /documents/{id}/embed
```

---

## Dependency Injection

```
app/

├── auth/
│   └── dependencies.py
│
├── db/
│   └── session.py
│
├── dependencies/
│   ├── __init__.py
│   └── upload.py
```

This structure is frozen.

---

## API Schemas

HTTP request/response models belong in:

```
app/schemas/
```

AI logic belongs in:

```
app/ai/
```

---

## Upload Service

UploadService is the orchestration layer.

Responsibilities:

* Validation
* Hashing
* Storage key generation
* S3 upload
* Metadata persistence
* Rollback
* Logging

Repositories never contain business logic.

Controllers remain thin.

---

# Current Implementation Status

## Phase 0 — Foundation ✅

Completed

* FastAPI
* Docker
* PostgreSQL
* Valkey
* Qdrant
* Configuration
* Logging
* Middleware
* Health endpoint
* Development tooling

---

## Phase 1 — Identity Platform ✅

Completed

* Configuration
* Database foundation
* User domain
* AWS Cognito
* JWT verification
* Authentication provider abstraction
* User synchronization
* Protected endpoints

Authentication is complete for current scope.

---

## Phase 2 — Knowledge Platform

### Milestone 2.1 — Document Upload ✅ COMPLETED

Completed:

* Document entity
* Alembic migration
* Repository
* Upload validator
* SHA-256 hashing
* Storage key generator
* Amazon S3 integration
* UploadService
* Dependency Injection
* Upload endpoint
* Structured logging
* End-to-end testing

Successfully verified:

* Authenticated upload
* Amazon S3 storage
* PostgreSQL persistence

Milestone documentation completed.

---

# Roadmap Traceability

## Phase 2 — Knowledge Platform

### ✅ 2.1 Document Upload

* Document upload
* S3 storage
* Metadata persistence

### ⏳ 2.2 Document Processing **NEXT**

* Processing pipeline
* File type detection
* PDF parser
* DOCX parser
* Markdown parser
* TXT parser
* Metadata extraction
* Processing status
* Processing errors
* Background processing
* Observability
* Evaluation

### ⏳ 2.3 Chunking Platform

Compare:

* Recursive
* Semantic
* Parent-child
* Agentic chunking

### ⏳ 2.4 Embedding Platform

Compare:

* BGE
* E5
* Nomic
* Instructor
* OpenAI

Batching

Caching

Retries

### ⏳ 2.5 Vector Platform

* Qdrant
* Collections
* Payloads
* Metadata
* Indexes

### ⏳ 2.6 Retrieval Platform

* Semantic search
* Hybrid search
* BM25
* MMR
* Filters

### ⏳ 2.7 Reranking

* Cross Encoder
* Late Interaction
* ColBERT research

### ⏳ 2.8 Knowledge Evaluation

* Precision
* Recall
* NDCG
* MRR
* Latency
* Cost

---

## Phase 3 — Conversation Platform

* Memory
* Sessions
* Streaming
* Semantic cache

---

## Phase 4 — Research Platform

* Planner
* Research Agent
* Reviewer
* Summarizer
* Report Generator
* Human Feedback

---

## Phase 5 — AI Agent Platform

* LangGraph
* Multi-agent workflows
* Checkpointing
* Interrupts
* Agent evaluation

---

## Phase 6 — MCP Platform

* MCP Client
* Registry
* Manager
* Research MCP
* Climate MCP
* Earthquake MCP

---

## Phase 7 — Evaluation Platform

* Retrieval evaluation
* Generation evaluation
* Agent evaluation
* Benchmarking
* LangSmith
* Phoenix

---

## Phase 8 — Production Platform

* Docker
* Kubernetes / ECS
* OpenTelemetry
* Prometheus
* Grafana
* CI/CD
* Security
* Performance

---

## Phase 9 — Enterprise Platform

* RBAC
* Multi-tenancy
* Billing
* Compliance
* Admin Portal
* Plugin Framework

---

# Current Focus

The backend foundation is complete.

The project now shifts primarily toward **AI Engineering**.

Every new milestone should emphasize:

* AI architecture
* Evaluation-driven development
* Model comparison
* Retrieval quality
* Prompt engineering
* AI observability
* Cost awareness
* Production AI engineering

---

# Immediate Next Milestone

## Phase 2.2 — Document Processing

This is the next implementation milestone.

The goal is to transform uploaded files into structured, normalized text that becomes the input for chunking, embeddings, retrieval, and ultimately the RAG pipeline.

We should begin by designing and implementing a modular document processing pipeline that supports multiple file formats while remaining extensible, measurable, and evaluation-driven.
