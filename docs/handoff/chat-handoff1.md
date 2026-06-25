# ResearchMind AI — Chat Handoff

> This document is the quick-start context for new ChatGPT conversations.
>
> The complete project documentation is available in `docs/project-handbook.md`.

---

# Project

ResearchMind AI

---

# Current Version

v0.1.0-foundation

---

# Project Vision

ResearchMind AI is a production-grade AI-powered Research & Intelligence Platform.

ResearchMind is **not** an MCP server.

ResearchMind orchestrates:

- AI reasoning
- RAG
- Memory
- LangGraph
- External MCP servers
- Report generation
- Evaluation
- Production infrastructure

---

# Core Architecture

```
User

↓

Next.js

↓

FastAPI

↓

LangGraph

↓

Internal RAG

↓

Memory

↓

External MCP Servers
```

---

# Tech Stack

Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- Pydantic v2
- uv

Frontend

- Next.js
- TypeScript
- Tailwind
- shadcn/ui

Infrastructure

- PostgreSQL
- Valkey
- Qdrant
- Docker Compose

Future

- LangGraph
- LangChain
- Celery
- Prometheus
- Grafana
- LangSmith

---

# Repository Structure

```
ResearchMind-AI/

apps/
agents/
services/
shared/
docs/
tests/
datasets/
benchmarks/
examples/
experiments/
infrastructure/
scripts/
tools/
```

---

# Backend Structure

```
apps/api/app/

api/
core/
db/
exceptions/
middleware/
models/
routers/
schemas/
services/
```

---

# Documentation Structure

```
docs/

architecture/
concepts/
engineering-journal/
adrs/
api/
deployment/
runbooks/
standards/
project-handbook.md
chat-handoff.md
```

---

# Completed Milestones

## Milestone 0.1

Completed

- uv
- FastAPI
- Docker
- PostgreSQL
- Valkey
- Qdrant

---

## Milestone 0.2

Completed

- Lifespan
- SQLAlchemy Async
- Dependency Injection
- Health Endpoints
- Middleware
- Logging
- Exception Handling
- API Contracts
- Typed Schemas

Documentation

- Engineering Journal
- Concepts
- Architecture
- ADRs
- API Docs

---

# Current Milestone

Milestone 0.3

Engineering Quality

Status

Next

---

# Next Tasks

Implement:

- Ruff
- MyPy
- Pytest
- Coverage
- Pre-commit
- GitHub Actions

After implementation:

- Update Engineering Journal
- Update Concepts
- Update Documentation

---

# Accepted Architecture Decisions

Completed ADRs

- ADR-001 Monorepo
- ADR-002 FastAPI
- ADR-003 FastAPI Lifespan
- ADR-004 Application State
- ADR-005 API Contracts
- ADR-006 Settings vs Constants
- ADR-007 Middleware Registration
- ADR-008 Typed API Schemas

Accepted ADRs should not be modified.

Future changes require new ADRs.

---

# MCP Strategy

ResearchMind consumes external MCP servers.

Each MCP has its own repository.

Examples

- Research MCP
- Climate Intelligence MCP
- Earthquake Intelligence MCP
- Crypto Intelligence MCP

ResearchMind remains domain-agnostic.

---

# Development Rules

Always:

- Follow the roadmap.
- Follow milestone order.
- Explain architectural reasoning before implementation.
- Follow official documentation.
- Prefer production-ready approaches.
- Avoid shortcuts.
- Keep documentation updated.

---

# Code Generation Rules

Always provide:

- Exact file path.
- Complete file contents.
- Required commands.
- Folder structure changes.

Avoid partial snippets unless explicitly requested.

---

# Documentation Rules

Every completed milestone must update:

- Engineering Journal
- Concepts
- Architecture
- ADRs
- API Documentation
- README (when appropriate)
- Changelog
- Project Status
- Roadmap

Documentation is part of the implementation.

---

# Current Goal

Complete Milestone 0.3 (Engineering Quality) before starting authentication and application features.

---

# How ChatGPT Should Continue

When continuing this project:

- Preserve the existing architecture.
- Do not change folder structure without discussion.
- Follow production engineering best practices.
- Explain trade-offs before implementation.
- Keep documentation synchronized with code.
- Build incrementally according to the roadmap.
- Always return complete files rather than partial snippets.