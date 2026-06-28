# ResearchMind AI — Technology Stack

**Version:** 1.0

---

# Purpose

This document defines the official technology stack for ResearchMind AI.

It records the technologies currently used, their purpose, architectural ownership, and future replacement strategy.

The technology stack should evolve deliberately rather than through ad-hoc adoption of new frameworks or libraries.

---

# Design Principles

Technology choices follow these principles:

* Production-oriented
* Well maintained
* Strong community adoption
* Replaceable where appropriate
* Best fit for AI engineering
* Cloud-native
* Observable
* Testable

Whenever practical, technologies should be abstracted so they can be replaced with minimal impact on business logic.

---

# Technology Status

| Status        | Meaning                                 |
| ------------- | --------------------------------------- |
| ✅ Adopted     | Currently used in production code       |
| 🟡 Planned    | Planned for future implementation       |
| 🔬 Evaluation | Used for comparison or experimentation  |
| ❌ Rejected    | Evaluated but intentionally not adopted |

---

# Programming Language

| Technology  | Status | Purpose                         |
| ----------- | ------ | ------------------------------- |
| Python 3.12 | ✅      | Primary backend and AI language |

## Reason

Python provides the strongest ecosystem for AI engineering, machine learning, orchestration frameworks, and production AI systems.

---

# Backend Framework

| Technology | Status | Purpose            |
| ---------- | ------ | ------------------ |
| FastAPI    | ✅      | REST API framework |

## Responsibilities

* REST APIs
* Dependency Injection
* Validation
* OpenAPI
* Request lifecycle

---

# Data Validation

| Technology  | Status | Purpose                      |
| ----------- | ------ | ---------------------------- |
| Pydantic v2 | ✅      | Validation and serialization |

Used for:

* API schemas
* Configuration
* AI models
* Structured outputs

---

# ORM

| Technology     | Status | Purpose      |
| -------------- | ------ | ------------ |
| SQLAlchemy 2.x | ✅      | Database ORM |

Responsibilities

* ORM models
* Query building
* Persistence
* Async database access

---

# Database Migration

| Technology | Status | Purpose                    |
| ---------- | ------ | -------------------------- |
| Alembic    | ✅      | Database schema migrations |

---

# Relational Database

| Technology | Status | Purpose              |
| ---------- | ------ | -------------------- |
| PostgreSQL | ✅      | Application metadata |

Stores:

* Users
* Documents
* Conversations
* Research sessions
* Evaluation results
* Metadata

Never stores document binaries.

---

# Object Storage

| Technology | Status | Purpose          |
| ---------- | ------ | ---------------- |
| Amazon S3  | ✅      | Document storage |

Stores:

* Original documents
* Future parsed files
* Future OCR output
* Future generated assets

---

# Cache

| Technology | Status | Purpose                    |
| ---------- | ------ | -------------------------- |
| Valkey     | ✅      | Cache and future messaging |

Planned uses:

* Semantic cache
* Response cache
* Embedding cache
* Session cache

---

# Vector Database

| Technology | Status | Purpose       |
| ---------- | ------ | ------------- |
| Qdrant     | ✅      | Vector search |

Responsibilities

* Embeddings
* Similarity search
* Metadata filtering
* Hybrid search

---

# Authentication

| Technology  | Status | Purpose           |
| ----------- | ------ | ----------------- |
| AWS Cognito | ✅      | Identity provider |

Responsibilities

* Authentication
* User management
* JWT issuance

Passwords are never stored inside ResearchMind.

---

# AI Framework

| Technology  | Status | Purpose                                     |
| ----------- | ------ | ------------------------------------------- |
| LangChain   | ✅      | LLM orchestration                           |
| LangGraph   | 🟡     | Multi-agent workflows                       |
| LangSmith   | 🟟     | Tracing and evaluation                      |
| Pydantic AI | 🔬     | Framework comparison and selected workflows |

---

# LLM Providers

Initial providers:

| Provider   | Status |
| ---------- | ------ |
| Groq       | ✅      |
| OpenRouter | ✅      |

Future providers:

| Provider     | Status |
| ------------ | ------ |
| OpenAI       | 🟡     |
| Anthropic    | 🟡     |
| Gemini       | 🟡     |
| Ollama       | 🟡     |
| Azure OpenAI | 🟡     |

Provider selection should remain transparent to business logic through the AI Core.

---

# Embedding Models

These models will be benchmarked before selecting defaults.

| Model             | Status |
| ----------------- | ------ |
| BGE               | 🟡     |
| E5                | 🟡     |
| Nomic             | 🟡     |
| Instructor        | 🟡     |
| OpenAI Embeddings | 🟡     |

Selection will be based on:

* Retrieval quality
* Latency
* Cost
* Vector dimensions
* Domain performance

---

# AI Core

The AI Core provides reusable AI infrastructure.

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

The AI Core is provider independent.

---

# AI Evaluation

Evaluation is treated as a first-class engineering capability.

Future metrics include:

## Retrieval

* Precision
* Recall
* NDCG
* MRR

## Generation

* Groundedness
* Faithfulness
* Citation quality

## Agents

* Planning quality
* Tool success
* Completion rate

---

# Observability

Current

| Technology | Status |
| ---------- | ------ |
| Structlog  | ✅      |

Future

| Technology    | Status |
| ------------- | ------ |
| LangSmith     | 🟡     |
| OpenTelemetry | 🟡     |
| Prometheus    | 🟡     |
| Grafana       | 🟡     |

Observability should grow incrementally throughout the project.

---

# Testing

| Technology | Status |
| ---------- | ------ |
| Pytest     | ✅      |

Future testing includes:

* Unit tests
* Integration tests
* End-to-end tests
* AI evaluation tests
* Regression benchmarks
* Performance testing

---

# Code Quality

| Technology | Status |
| ---------- | ------ |
| Ruff       | ✅      |
| MyPy       | ✅      |
| Pre-commit | ✅      |

These tools maintain code consistency throughout the project.

---

# Dependency Management

| Technology | Status |
| ---------- | ------ |
| uv         | ✅      |

Responsibilities

* Package management
* Virtual environments
* Dependency locking

---

# Containerization

| Technology     | Status |
| -------------- | ------ |
| Docker         | ✅      |
| Docker Compose | ✅      |

Used for:

* Local development
* Infrastructure services
* Future deployment

---

# Cloud Platform

| Technology | Status |
| ---------- | ------ |
| AWS        | ✅      |

Current AWS services

* Cognito
* S3

Planned AWS services

* ECS or EKS (decision later)
* CloudWatch
* IAM
* Secrets Manager

---

# Future Infrastructure

| Technology       | Status |
| ---------------- | ------ |
| Kubernetes / ECS | 🟡     |
| GitHub Actions   | 🟡     |
| OpenTelemetry    | 🟡     |
| Prometheus       | 🟡     |
| Grafana          | 🟡     |

These technologies belong to the Production Platform phase.

---

# Technology Selection Strategy

Technology adoption follows this order:

1. Research
2. Small experiment
3. Benchmark
4. Evaluation
5. Architecture review
6. Adoption
7. Documentation

This ensures new technologies are introduced intentionally rather than reactively.

---

# Technology Evolution

Some technologies are intentionally abstracted behind interfaces.

Examples include:

* LLM providers
* Embedding models
* Storage providers
* Vector databases
* Prompt implementations

This allows experimentation without requiring major architectural changes.

---

# Frozen Core Stack

The following technologies are considered part of the project's stable foundation.

## Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL

## AI

* LangChain
* LangSmith
* Groq
* OpenRouter

## Infrastructure

* Amazon S3
* Valkey
* Qdrant

## Authentication

* AWS Cognito

These technologies form the current production foundation of ResearchMind AI.

Future milestones should extend this stack rather than replace it unless a measurable engineering reason exists.

---

# Guiding Principle

Technology choices should serve the architecture—not define it.

ResearchMind is designed around modular, replaceable components so that models, providers, infrastructure, and AI capabilities can evolve without requiring fundamental changes to the overall system architecture.
