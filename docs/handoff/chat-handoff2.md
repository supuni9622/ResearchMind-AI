# ResearchMind AI — Chat Handoff

## Purpose

This document is the primary context handoff for continuing ResearchMind AI across new ChatGPT conversations.

The goal is that a new conversation can immediately continue implementation without losing architectural decisions, engineering standards, roadmap progress, or project context.

This document should be updated after every completed milestone.

---

# Project Overview

ResearchMind AI is a production-oriented AI research platform designed to demonstrate professional AI engineering practices rather than simply integrating LLM APIs.

The project emphasizes:

* Retrieval-Augmented Generation (RAG)
* Agentic AI
* LangGraph
* Model Context Protocol (MCP)
* AI Evaluation
* Production backend engineering
* AWS deployment
* Observability
* Security
* Clean architecture
* Strong documentation

The objective is to build a portfolio-quality system that reflects how production AI platforms are engineered.

---

# Engineering Philosophy

The project is intentionally built as a production-ready system.

However, implementation should remain pragmatic.

Avoid unnecessary enterprise complexity.

When a trade-off exists:

* Prefer simplicity.
* Introduce abstractions only when they provide clear long-term value.
* Keep the focus on AI engineering rather than infrastructure engineering.

---

# Current Technology Stack

Backend

* Python 3.12
* FastAPI
* SQLAlchemy 2.x
* Alembic
* Pydantic v2
* Structlog

AI

* LangChain
* LangGraph
* Groq
* Qdrant
* Sentence Transformers

Infrastructure

* PostgreSQL
* Valkey
* Qdrant
* Docker Compose

Development

* uv
* Ruff
* MyPy
* Pytest
* Pre-commit

Future

* AWS Cognito
* Amazon S3
* Docker
* Kubernetes

---

# Current Project Status

Completed

Phase 0 — Foundation

* Project architecture
* Documentation structure
* Development environment
* Docker infrastructure
* FastAPI application
* Settings management
* Structured logging
* Middleware
* Health endpoint
* Code quality tooling
* Testing setup

Phase 1

Milestone 1.1

Completed

* Environment configuration
* Settings refactoring

Milestone 1.2

Completed

* SQLAlchemy
* Database engine
* Alembic integration

Milestone 1.3

In Progress

Currently implementing:

Internal User Domain

---

# Architectural Decisions

Authentication

ResearchMind never stores passwords.

Authentication will be delegated to an external Identity Provider.

Current implementation target:

AWS Cognito

ResearchMind owns:

* Users
* Research Sessions
* Documents
* Reports
* AI Memory
* Preferences

Identity Provider owns:

* Authentication
* Passwords
* MFA
* OAuth
* JWT

---

User Model

ResearchMind maintains its own User entity independent of Cognito.

Mapping:

AWS Cognito User

↓

ResearchMind User

↓

Research Sessions

↓

Documents

↓

Memory

↓

Reports

↓

Preferences

---

Authentication Architecture

Authentication Provider

↓

Authentication Service

↓

AWS Cognito

Future providers should be replaceable without changing application business logic.

---

Observability

Observability is treated as a cross-cutting concern rather than a separate implementation phase.

Logging

Metrics

Tracing

Evaluation

Cost Tracking

are added progressively throughout development.

---

Evaluation

Evaluation is also a cross-cutting capability.

Every AI component should eventually have measurable quality metrics.

Examples:

* Retrieval Precision
* Recall
* Faithfulness
* Groundedness
* Citation Quality
* Latency
* Cost

---

Development Workflow

For every milestone:

1. Requirements
2. Architecture
3. Design Decisions
4. Implementation
5. Testing
6. Documentation
7. Review
8. Commit

Avoid recursive documentation.

Documentation should support implementation rather than delay progress.

---

Implementation Rules

Always explain architecture before implementation.

Provide complete files.

Never provide partial snippets unless explicitly requested.

Prefer official documentation and best practices.

Avoid unnecessary abstractions.

Keep implementation incremental.

Keep commits small and logical.

---

Roadmap

Phase 1

Identity & User Platform

1.1 Configuration ✅

1.2 Database Foundation ✅

1.3 Internal User Domain (Current)

1.4 Authentication Integration

* Authentication abstraction
* AWS Cognito
* JWT validation
* Current user dependency

1.5 Authorization

* Roles
* Permissions
* Ownership

1.6 User Profile

---

Future Phases

Phase 2

Core RAG

Phase 3

Production Chat

Phase 4

Research Workflow

Phase 5

Evaluation

Phase 6

Production Engineering

Phase 7

Agent Platform

Phase 8

MCP Integration

Phase 9

Production Deployment

Phase 10

Enterprise Features

---

How ChatGPT Should Collaborate

Act as a senior AI engineer and technical architect.

Challenge architectural decisions when appropriate.

Prioritize maintainability and production readiness.

Balance engineering quality with implementation speed.

Keep the project focused on AI engineering rather than over-engineering infrastructure.

Explain trade-offs.

Prefer iterative implementation over large rewrites.

Never lose track of previous architectural decisions.

Always continue from the current milestone unless explicitly instructed otherwise.

---

Next Task

Continue Milestone 1.3.

Current objective:

Implement the Internal User Domain.

Next implementation order:

* User model
* Alembic migration
* Repository
* Service
* Tests
* Documentation

After Milestone 1.3:

Proceed to Authentication Integration using AWS Cognito.
