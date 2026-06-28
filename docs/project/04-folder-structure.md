# ResearchMind AI — Folder Structure

**Version:** 1.0

---

# Purpose

This document defines the high-level folder structure of the ResearchMind AI backend.

It establishes ownership and responsibility for each directory to ensure architectural consistency as the project grows.

The folder structure should evolve only when required by new capabilities and should avoid unnecessary reorganization.

---

# Design Principles

The folder structure follows several principles.

* Separation of concerns
* Feature-oriented AI modules
* Infrastructure abstraction
* Thin HTTP layer
* Service orchestration
* Replaceable AI components
* Production-ready organization

---

# High-Level Structure

```text
apps/api/

├── alembic/
├── app/
├── tests/
├── docs/
└── pyproject.toml
```

---

# Application Structure

```text
app/

├── ai/
├── api/
├── auth/
├── core/
├── db/
├── dependencies/
├── exceptions/
├── infrastructure/
├── models/
├── repositories/
├── schemas/
├── services/
└── main.py
```

---

# Folder Responsibilities

---

## app/ai/

### Purpose

Contains AI-specific business capabilities.

This is the heart of the project and will continue growing throughout development.

Examples

* Knowledge Platform
* Chunking
* Embeddings
* Retrieval
* Reranking
* Evaluation
* Agents
* Memory
* MCP

Example structure

```text
ai/

├── core/
├── knowledge/
├── retrieval/
├── evaluation/
├── prompts/
├── memory/
├── agents/
├── mcp/
└── shared/
```

This folder owns AI engineering.

---

## app/ai/core/

### Purpose

Contains reusable AI infrastructure.

Current architecture

```text
core/

├── providers/
├── router/
├── prompts/
├── embeddings/
├── retrieval/
├── evaluation/
├── registry/
├── cost/
├── tokens/
└── config/
```

Responsibilities

* Provider registry
* Model routing
* Prompt registry
* Shared AI configuration
* Cost tracking
* Token tracking
* Model registry

This folder should remain provider independent.

---

## app/api/

### Purpose

HTTP interface.

Responsibilities

* Routes
* Request validation
* Response serialization
* HTTP concerns

API controllers remain thin.

No business logic belongs here.

---

## app/auth/

### Purpose

Authentication and authorization.

Responsibilities

* JWT verification
* Identity providers
* Current user
* Future RBAC

Passwords are never managed by ResearchMind.

---

## app/core/

### Purpose

Application-wide configuration.

Responsibilities

* Settings
* Constants
* Lifespan
* Startup configuration
* Logging configuration

No business logic belongs here.

---

## app/db/

### Purpose

Database infrastructure.

Responsibilities

* Base model
* Session management
* Mixins
* Database utilities

---

## app/dependencies/

### Purpose

Dependency Injection.

Responsibilities

Construct application services.

Examples

```text
upload.py
processing.py
retrieval.py
chat.py
```

Business logic should never construct infrastructure directly.

---

## app/exceptions/

### Purpose

Application exceptions.

Responsibilities

* Base exceptions
* Domain exceptions
* HTTP mapping

Every subsystem should define its own domain exceptions.

---

## app/infrastructure/

### Purpose

External systems.

Responsibilities

* Amazon S3
* Hashing
* Future queues
* Email
* Storage
* OCR integrations

Infrastructure should remain replaceable.

Business logic depends on interfaces, not implementations.

---

## app/models/

### Purpose

SQLAlchemy ORM entities.

Examples

* User
* Document
* Future Conversation
* ResearchSession

Models represent persisted state.

---

## app/repositories/

### Purpose

Persistence layer.

Responsibilities

* Database operations
* Queries
* Entity persistence

Repositories never:

* Call APIs
* Upload files
* Perform business logic
* Commit transactions

---

## app/schemas/

### Purpose

HTTP request and response models.

Examples

```text
user.py
document.py
conversation.py
research.py
```

Only API contracts belong here.

Internal AI models remain inside app/ai.

---

## app/services/

### Purpose

General application services.

Examples

* UserService
* NotificationService

AI workflows belong inside app/ai instead.

---

# AI Module Structure

The AI platform is organized by capability rather than technology.

```text
ai/

├── core/
│
├── knowledge/
│   ├── upload/
│   ├── processing/
│   ├── chunking/
│   ├── embeddings/
│   ├── vector/
│   ├── retrieval/
│   └── reranking/
│
├── conversation/
│
├── evaluation/
│
├── memory/
│
├── agents/
│
├── mcp/
│
└── shared/
```

Each capability owns its implementation.

---

# Knowledge Platform

Current implementation

```text
knowledge/

└── upload/
```

Future structure

```text
knowledge/

├── upload/
├── processing/
├── parsers/
├── chunking/
├── embeddings/
├── vector/
├── retrieval/
├── reranking/
└── evaluation/
```

This entire module becomes the RAG pipeline.

---

# AI Core

The AI Core provides reusable infrastructure shared across the platform.

```text
core/

├── providers/
├── router/
├── prompts/
├── embeddings/
├── retrieval/
├── registry/
├── evaluation/
├── cost/
├── tokens/
└── config/
```

Responsibilities

* Provider abstraction
* Model routing
* Prompt management
* Shared evaluation
* Cost tracking
* Token accounting

The AI Core must remain independent from any specific provider.

---

# Infrastructure Layer

Current

```text
infrastructure/

├── hashing/
└── storage/
```

Future

```text
infrastructure/

├── hashing/
├── storage/
├── queue/
├── ocr/
├── cache/
├── messaging/
└── monitoring/
```

Infrastructure implementations remain isolated.

---

# Documentation Structure

```text
docs/

├── project/
│
├── architecture/
│
├── adr/
│
└── ai/
```

---

## Project Documentation

```text
project/

00-project-constitution.md
01-current-state.md
02-roadmap.md
03-frozen-decisions.md
04-folder-structure.md
05-tech-stack.md
06-chatgpt-collaboration.md
07-engineering-journal.md
```

---

## Milestone Documentation

```text
ai/

knowledge-platform/

    2.1-document-upload/

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

Every milestone follows the same documentation structure.

---

# Ownership Rules

| Folder         | Owns                         |
| -------------- | ---------------------------- |
| api            | HTTP                         |
| auth           | Identity                     |
| core           | Application configuration    |
| db             | Database infrastructure      |
| dependencies   | Dependency Injection         |
| infrastructure | External systems             |
| models         | ORM entities                 |
| repositories   | Persistence                  |
| schemas        | HTTP contracts               |
| services       | General application services |
| ai             | AI engineering               |

Each folder should own a single responsibility.

---

# Folder Evolution

The folder structure is considered stable.

Future milestones should extend existing folders rather than reorganize the project.

Structural changes should occur only when they provide clear production value.

The primary engineering effort should now focus on building AI capabilities rather than reorganizing the backend.

---

# Guiding Principle

The folder structure exists to make ownership obvious.

A new engineer should be able to determine where new functionality belongs without needing architectural discussions.

As ResearchMind grows, implementation should naturally extend this structure while preserving separation of concerns and keeping AI engineering at the center of the project.
