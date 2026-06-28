# ResearchMind AI — Frozen Engineering Decisions

**Version:** 1.0

---

# Purpose

This document records architectural and engineering decisions that have been accepted and frozen for the ResearchMind AI project.

The goal is to maintain architectural consistency, reduce unnecessary redesign discussions, and preserve long-term project continuity across development milestones and ChatGPT conversations.

A frozen decision should only be revisited when there is a strong production justification, such as:

* Security
* Scalability
* Performance
* Reliability
* AI engineering requirements
* Significant change in project scope

Personal preference or alternative implementation styles are not sufficient reasons to reopen a decision.

---

# Decision Status

| Status          | Meaning                                                     |
| --------------- | ----------------------------------------------------------- |
| ✅ Frozen        | Accepted and should not change without strong justification |
| 🟡 Review Later | Intentionally postponed for a future milestone              |
| 🔴 Replaced     | Superseded by a newer decision                              |

---

# Project-Level Decisions

---

## FD-001 — AI-First Project

**Status:** ✅ Frozen

### Decision

ResearchMind is an AI Engineering project.

Backend engineering exists to support AI capabilities rather than being the primary objective.

### Reason

The project's purpose is to develop expertise in production AI systems including RAG, retrieval, evaluation, agents, and observability.

---

## FD-002 — Vertical Slice Development

**Status:** ✅ Frozen

### Decision

The platform is implemented milestone by milestone using vertical slices.

Every milestone should produce a working capability before moving to the next.

### Reason

Maintains continuous progress and reduces integration risk.

---

## FD-003 — Production Over Perfection

**Status:** ✅ Frozen

### Decision

Prefer practical production-quality implementation over theoretical perfection.

### Reason

Avoids unnecessary redesign and analysis paralysis.

---

# Architecture Decisions

---

## FD-004 — Separation of Concerns

**Status:** ✅ Frozen

### Decision

The application follows a layered architecture.

```text
API

↓

Service

↓

Infrastructure

↓

Repository

↓

Database
```

Each layer owns a single responsibility.

### Reason

Improves maintainability, testability, and long-term scalability.

---

## FD-005 — Thin API Layer

**Status:** ✅ Frozen

### Decision

API endpoints remain thin.

Business logic belongs in services.

### Reason

Keeps HTTP concerns separate from application workflows.

---

## FD-006 — Repository Pattern

**Status:** ✅ Frozen

### Decision

Repositories own persistence only.

Repositories must never:

* Perform business logic
* Call external services
* Commit transactions
* Handle authentication

### Reason

Clear ownership and separation of concerns.

---

## FD-007 — Service Orchestration

**Status:** ✅ Frozen

### Decision

Business workflows are coordinated by dedicated services.

Example

* UploadService
* Future ProcessingService
* Future ChunkingService

### Reason

Keeps workflows centralized and reusable.

---

## FD-008 — Dependency Injection

**Status:** ✅ Frozen

### Decision

Dependency construction belongs in:

```text
app/dependencies/
```

Business logic never creates infrastructure objects directly.

### Reason

Supports modularity and testing.

---

# AI Architecture Decisions

---

## FD-009 — AI Core

**Status:** ✅ Frozen

### Decision

The AI platform is organized around a dedicated AI Core.

```text
AI Core

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
```

### Reason

Provides a modular and provider-independent AI architecture.

---

## FD-010 — Provider Strategy

**Status:** ✅ Frozen

### Decision

Initial providers:

* Groq
* OpenRouter

Future providers:

* OpenAI
* Anthropic
* Ollama
* Gemini
* Azure OpenAI

### Reason

Supports experimentation while remaining provider independent.

---

## FD-011 — LangSmith

**Status:** ✅ Frozen

### Decision

LangSmith is integrated from the beginning of LangChain development.

### Reason

Tracing, debugging, and evaluation should grow alongside the AI platform rather than being introduced later.

---

## FD-012 — AI Evaluation

**Status:** ✅ Frozen

### Decision

Evaluation is treated as a first-class capability.

Every AI subsystem should eventually be measurable.

### Reason

Engineering decisions should be driven by evidence rather than intuition.

---

# Storage Decisions

---

## FD-013 — Binary Storage

**Status:** ✅ Frozen

### Decision

Original documents are stored in Amazon S3.

### Reason

Object storage is scalable, durable, and the industry standard for document management.

---

## FD-014 — Metadata Storage

**Status:** ✅ Frozen

### Decision

PostgreSQL stores document metadata only.

Binary content is never stored in PostgreSQL.

### Reason

Separates structured metadata from large binary objects.

---

## FD-015 — Storage Layout

**Status:** ✅ Frozen

### Decision

Document storage follows a deterministic directory structure.

```text
documents/

    {owner_id}/

        {document_id}/

            original.pdf
```

Future generated artifacts remain inside the same directory.

### Reason

Simplifies lifecycle management and derivative asset generation.

---

# Authentication Decisions

---

## FD-016 — Identity Provider

**Status:** ✅ Frozen

### Decision

AWS Cognito is responsible for authentication.

ResearchMind never stores user passwords.

### Reason

Delegating identity management improves security and reduces implementation complexity.

---

## FD-017 — Current User

**Status:** ✅ Frozen

### Decision

Authenticated users are resolved through:

```text
get_current_user()
```

Business services receive an authenticated ResearchMind User.

### Reason

Authentication remains centralized and reusable.

---

# API Decisions

---

## FD-018 — API Schemas

**Status:** ✅ Frozen

### Decision

HTTP request and response models belong in:

```text
app/schemas/
```

AI-specific models remain inside:

```text
app/ai/
```

### Reason

Separates transport models from internal AI models.

---

## FD-019 — Document Endpoint

**Status:** ✅ Frozen

### Decision

Upload endpoint

```text
POST /api/v1/documents/upload
```

Future document endpoints

```text
GET    /documents

GET    /documents/{id}

DELETE /documents/{id}

POST   /documents/upload

POST   /documents/{id}/reprocess

POST   /documents/{id}/chunk

POST   /documents/{id}/embed
```

### Reason

Maintains RESTful resource organization while treating upload as an action.

---

# Documentation Decisions

---

## FD-020 — Milestone Documentation

**Status:** ✅ Frozen

### Decision

Every milestone maintains its own documentation.

```text
README
Architecture
Implementation
Observability
Evaluation
Runbook
ADR
Changelog
Retrospective
```

### Reason

Documentation grows together with implementation.

---

## FD-021 — Project Memory

**Status:** ✅ Frozen

### Decision

Long-term project continuity is maintained through:

```text
docs/project/

00-project-constitution.md
01-current-state.md
02-roadmap.md
03-frozen-decisions.md
04-folder-structure.md
05-tech-stack.md
06-chatgpt-collaboration.md
07-engineering-journal.md
```

### Reason

Supports seamless continuation across multiple ChatGPT conversations and long-term development.

---

# Collaboration Decisions

---

## FD-022 — Implementation Style

**Status:** ✅ Frozen

### Decision

Every implementation should include:

* Exact file paths
* Complete file contents
* Explanation of the implementation
* Commands
* Verification steps
* Commit message

Partial snippets should only be used when explicitly requested.

### Reason

Improves implementation quality and reduces ambiguity.

---

## FD-023 — Architecture Discussions

**Status:** ✅ Frozen

### Decision

Avoid repeated architecture discussions after a decision has been implemented.

Architecture should only be revisited when there is a production justification.

### Reason

Prevents architectural drift and keeps development focused on implementation.

---

## FD-024 — AI-Focused Discussions

**Status:** ✅ Frozen

### Decision

As the backend foundation is complete, future discussions should primarily focus on AI engineering, experimentation, evaluation, and production AI capabilities.

### Reason

Aligns engineering effort with the primary objective of the project.

---

# Future Decisions

Future architectural decisions should be added to this document as they become permanent.

Examples include:

* Chunking strategy selection
* Embedding model selection
* Default retrieval pipeline
* Reranker selection
* Prompt management strategy
* LangGraph architecture
* Memory architecture
* MCP architecture
* Deployment strategy

Each accepted decision should receive a new Frozen Decision (FD) identifier.

---

# Guiding Rule

Once a decision is marked **Frozen**, implementation should move forward.

Do not reopen previously accepted decisions unless there is a demonstrable production reason.

This discipline ensures ResearchMind evolves through implementation, experimentation, and measurable improvement rather than repeated architectural redesign.
