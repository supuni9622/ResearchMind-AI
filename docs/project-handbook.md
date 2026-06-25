# ResearchMind AI — Project Handbook

> **Version:** 0.1.0  
> **Last Updated:** 2026-06-25  
> **Status:** Active Development

---

# Purpose

This handbook is the **single source of truth** for the ResearchMind AI project.

It documents the project's vision, architecture, roadmap, engineering standards, implementation strategy, documentation practices, and collaboration workflow.

Every implementation decision should align with this handbook.

Whenever a new ChatGPT conversation begins, this document should be treated as the primary project context.

---

# Project Vision

ResearchMind AI is a production-grade AI-powered Research & Intelligence Platform.

Unlike a traditional chatbot, ResearchMind combines:

- AI reasoning
- Retrieval-Augmented Generation (RAG)
- Multi-agent orchestration
- Long-term memory
- Internal knowledge retrieval
- External MCP integrations
- Structured report generation
- Evaluation
- Production observability

The goal is to build a modular AI platform that can expand into multiple domains without changing its core architecture.

---

# Long-Term Goals

Build a portfolio-quality AI platform that demonstrates modern AI engineering practices.

The project should showcase:

- Backend engineering
- AI engineering
- RAG systems
- LangGraph workflows
- MCP integrations
- Distributed systems
- Production infrastructure
- Observability
- Evaluation
- Documentation

This repository should represent production engineering rather than tutorial code.

---

# Core Philosophy

ResearchMind is **not** an MCP server.

ResearchMind is an AI orchestration platform.

Responsibilities:

- Understand user intent
- Plan research workflows
- Select required MCPs
- Retrieve internal knowledge
- Combine information
- Reason over results
- Generate reports
- Evaluate outputs
- Maintain memory

External MCP servers remain independent capability providers.

---

# Technology Stack

## Backend

- Python 3.12
- FastAPI
- SQLAlchemy 2.x
- Pydantic v2
- uv

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

## Databases

- PostgreSQL
- Valkey
- Qdrant

## AI

- LangChain
- LangGraph
- OpenAI Compatible APIs
- Groq (development)
- OpenAI / Anthropic (future)

## Infrastructure

- Docker Compose
- GitHub Actions
- Prometheus
- Grafana
- LangSmith

---

# High-Level Architecture

```
                 User
                  │
                  ▼
          Next.js Frontend
                  │
                  ▼
           FastAPI Backend
                  │
                  ▼
        LangGraph Orchestrator
                  │
      ┌───────────┼────────────┐
      ▼           ▼            ▼
 Internal RAG   Memory      MCP Clients
      │           │            │
      ▼           ▼            ▼
 Qdrant      Valkey      External MCP Servers
```

---

# External MCP Strategy

ResearchMind consumes external MCP servers.

Each MCP lives in an independent repository.

Examples:

- Research MCP
- Climate Intelligence MCP
- Earthquake Intelligence MCP
- Crypto Intelligence MCP
- Space Intelligence MCP

ResearchMind should never contain domain-specific logic.

The planner determines which MCPs are required for each request.

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

README.md

architecture/
concepts/
engineering-journal/
adrs/
api/
deployment/
runbooks/
standards/
```

Every documentation folder contains its own README.

---

# Documentation Standards

Every milestone updates:

- Engineering Journal
- Concepts
- Architecture
- ADRs
- API Documentation
- Project Status
- Roadmap
- Changelog

Documentation is considered part of the implementation.

A milestone is not complete until its documentation is complete.

---

# ADR Standards

Architecture Decision Records follow a consistent template:

- Context
- Problem Statement
- Decision
- Alternatives
- Consequences
- Implementation Notes
- Related Documents

Accepted ADRs are immutable.

New architectural changes should create new ADRs rather than modifying accepted ones.

---

# Engineering Standards

The project follows these principles:

- Clean Architecture
- Separation of Concerns
- Dependency Injection
- Strong Typing
- Async First
- Production Readiness
- Testability
- Explicit Dependencies
- Clear Ownership
- Modular Design

---

# Coding Standards

When implementing features:

- Use typed Pydantic schemas.
- Prefer dependency injection.
- Avoid global state.
- Separate business logic from routers.
- Use async where appropriate.
- Keep modules focused on a single responsibility.

---

# AI Engineering Standards

The project should demonstrate:

- RAG
- Hybrid Retrieval
- Semantic Search
- LangGraph
- Memory
- Checkpointing
- Semantic Cache
- Evaluation
- Multi-Agent Systems
- MCP Integration

---

# How ChatGPT Should Guide This Project

The implementation should follow these rules.

## 1. Full Files

Always provide complete file contents.

Do not provide partial snippets unless specifically requested.

---

## 2. Explain the Reasoning

Before implementation, explain:

- Why the change is needed
- Architectural reasoning
- Trade-offs
- Best practices
- Real-world usage

---

## 3. Follow Official Documentation

Recommendations should align with:

- FastAPI
- SQLAlchemy
- Pydantic
- LangChain
- LangGraph
- OpenTelemetry
- Docker
- Modern Python practices

---

## 4. Think Like a Senior Engineer

Avoid tutorial shortcuts.

Choose approaches suitable for production systems.

---

## 5. Build Incrementally

Follow the roadmap.

Do not skip milestones.

Every milestone builds on previous work.

---

## 6. Keep Documentation Updated

Whenever implementation changes:

Update the relevant documentation before moving to the next milestone.

---

## 7. Preserve Context

Maintain consistency with:

- Architecture
- Folder structure
- Technology choices
- Naming conventions
- Documentation style

Do not introduce conflicting approaches.

---

# Milestones

## Phase 0 — Foundation

### Milestone 0.1

- Project Setup
- uv
- FastAPI
- Docker
- PostgreSQL
- Valkey
- Qdrant

Status: ✅ Completed

---

### Milestone 0.2

Backend Foundation

Completed:

- Lifespan
- SQLAlchemy
- Dependency Injection
- Health Checks
- Middleware
- Logging
- Exception Handling
- API Contracts
- Typed Schemas
- Documentation

Status: ✅ Completed

---

### Milestone 0.3

Engineering Quality

Planned:

- Ruff
- MyPy
- Pytest
- Coverage
- Pre-commit
- GitHub Actions

Status: ⏳ Next

---

## Phase 1

Authentication

- Alembic
- Users
- JWT
- Refresh Tokens
- Authorization

---

## Phase 2

Knowledge Platform

- Upload Documents
- Chunking
- Embeddings
- Qdrant Indexing

---

## Phase 3

Research Platform

- RAG
- Citations
- Reports
- Evaluation

---

## Phase 4

AI Platform

- LangGraph
- Multi-Agent
- Memory
- Checkpointing
- Semantic Cache

---

## Phase 5

MCP Platform

- MCP Client Registry
- Research MCP
- Climate MCP
- Earthquake MCP
- Cross-domain reasoning

---

## Phase 6

Production

- Monitoring
- Observability
- Scaling
- Deployment
- Kubernetes
- Performance Optimization

---

# Current Progress

Current Version

```
v0.1.0-foundation
```

Completed

- Foundation
- Backend
- Documentation

Current Focus

```
Milestone 0.3
Engineering Quality
```

---

# Definition of Done

A milestone is complete only when:

- Code implemented
- Tests passing
- Documentation updated
- Engineering Journal updated
- Concepts documented
- ADRs created (if applicable)
- API documentation updated
- Changelog updated
- Project Status updated
- Roadmap updated

---

# Long-Term Goal

ResearchMind AI should become a portfolio-quality AI platform that demonstrates modern backend engineering, AI engineering, and production architecture.

The final repository should reflect the standards expected in professional software engineering teams and serve as a flagship project showcasing production-ready AI systems.