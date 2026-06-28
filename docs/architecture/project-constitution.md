📖 ResearchMind AI Architecture Handbook (Frozen v1.0)

This becomes the single entry point for the project.

1. Project Constitution
Vision

ResearchMind AI is a production-grade AI research platform built to demonstrate modern AI Engineering practices rather than simple LLM API integration.

The project emphasizes engineering production AI systems that are measurable, observable, modular, evaluation-driven and replaceable.

The objective is to become an AI Integration Engineer capable of designing, deploying, evaluating and operating enterprise AI systems.

Primary Goal

The project is an AI Engineering project.

Backend engineering exists only to support the AI platform.

Priority order:

AI Engineering
↓

Architecture

↓

Evaluation

↓

Production

↓

Backend
Non Goals

ResearchMind will NOT build

Custom LLMs
Custom embedding models
Custom vector databases
Custom rerankers
Custom workflow engine
ML model training

ResearchMind focuses on orchestration, integration, evaluation and production AI engineering.

Engineering Principles
AI First
Separation of Concerns
Replaceability
Evaluation Driven Development
Observability by Default
Everything Important is Measurable
Decision Process

Architectural decisions are frozen.

Changes require an ADR and a real implementation reason.

No speculative redesign.

2. AI Architecture (Frozen)

This is the core architecture of ResearchMind.

Applications
        │
        ▼
──────────────────────────────
          AI Core
──────────────────────────────
        │
 ┌──────┼──────┐
 ▼      ▼      ▼
Runtime Knowledge Quality
        │
        ▼
    AI Registry
        │
        ▼
    AI Guardrails
        │
        ▼
 External Providers
AI Runtime

Responsible for inference.

Contains

Provider Registry
Model Registry
Model Router
Prompt Registry
Structured Output
Streaming
Tool Calling
Retry Strategy
Timeout Strategy
Fallback Strategy
AI Knowledge

Responsible for RAG.

Contains

Upload
Document Intelligence
Chunking
Embeddings
Vector Store
Retrieval
Reranking
Knowledge Cache
AI Quality

Responsible for measurement.

Contains

LangSmith
Evaluation
Benchmarks
Prompt Versioning
Experiment Tracking
Regression Testing
Cost Tracking
Token Tracking
AI Registry

Central registry for AI components.

Contains

Providers
Models
Embeddings
Rerankers
Prompt Templates
Evaluators
MCP Servers
AI Guardrails

Responsible for AI safety.

Initially

Pass-through implementation

Future

Prompt Injection
PII Detection
Tool Policies
Safety Policies
3. Provider Strategy (Frozen)

Development Providers

Groq
↓

OpenRouter

Future Providers

OpenAI
Anthropic
Gemini
Azure OpenAI
Ollama
Bedrock

Application code must never directly call providers.

Everything goes through AI Runtime.

4. AI Framework (Frozen)

Core AI

LangChain
LangGraph
LangSmith

Comparison

PydanticAI

Future (only if justified)

LiteLLM

LangSmith starts from the very first LangChain implementation.

Tracing is mandatory.

5. Technology Stack (Frozen)
Backend
Python 3.12
FastAPI
SQLAlchemy
Alembic
Pydantic v2
Structlog
AI
LangChain
LangGraph
LangSmith
LLM Providers
Groq
OpenRouter
Embeddings
Sentence Transformers
BGE
E5
Nomic
Instructor
OpenAI (comparison)
Vector Database
Qdrant
Storage
PostgreSQL
Valkey
Amazon S3 (later)
Evaluation
DeepEval
Ragas
LangSmith
Custom Benchmarks
Observability
Structlog
LangSmith
OpenTelemetry
Prometheus
Grafana
Phoenix
Infrastructure
Docker
Docker Compose
GitHub Actions
AWS
6. Engineering Workflow (Frozen)

Every milestone follows exactly the same lifecycle.

1 Problem

2 Requirements

3 Architecture

4 ADR (if needed)

5 API & Data Contracts

6 Implementation

7 Testing

8 Observability

9 Evaluation

10 Documentation

11 Production Review

12 Commit

13 Retrospective

No milestone skips these steps.

7. Cross-Cutting Capabilities (Frozen)

Every subsystem includes these concerns from the beginning.

Capability	From Phase
Logging	0
Metrics	0
Testing	0
Security	0
Documentation	0
Evaluation	2
LangSmith	2
Tracing	2
Cost Tracking	2
Engineering Analytics	2
Performance	0

These are continuous capabilities, not standalone phases.

8. Standard Milestone Template (Frozen)

Every milestone produces

architecture.md

implementation.md

testing.md

observability.md

evaluation.md

benchmarks.md

runbook.md

retrospective.md

Each subsystem owns its own documentation.

9. Evaluation Philosophy (Frozen)

Every AI feature defines

Success

What does good look like?

Example

Recall
Precision
NDCG
Operational Health
Latency
Failure Rate
Queue Length
Cache Hit Rate
Quality
Faithfulness
Groundedness
Citation Quality
Completeness
Cost
Tokens
Embeddings
LLM Cost
Regression
Golden Datasets
Benchmark History
Prompt Versions
Model Comparisons
10. Observability Philosophy (Frozen)

Every subsystem exposes

Logs

↓

Metrics

↓

Traces

↓

Dashboards

↓

Alerts

LangSmith becomes the AI observability platform.

OpenTelemetry becomes the platform observability layer.

11. Repository Boundaries (Frozen)
apps/

Applications only.

services/

Business capabilities.

agents/

LangGraph agents.

shared/

Reusable components.

datasets/

Evaluation datasets.

benchmarks/

Benchmark suites.

docs/

Architecture and engineering documentation.

No folder should contain responsibilities belonging to another layer.

12. Roadmap (Frozen)
Phase 0
Engineering Foundation ✅

Phase 1
Identity Platform ✅

Phase 2
Knowledge Platform (Core RAG)

Phase 3
AI Platform

Phase 4
Research Platform

Phase 5
Agent Platform

Phase 6
MCP Platform

Phase 7
AI Evaluation Platform

Phase 8
AI Observability & Production Platform

Phase 9
Enterprise Platform

Future phases may expand implementation but should not change the architecture without an ADR.

13. What We Will Not Revisit

Unless implementation exposes a real limitation, the following decisions are considered frozen:

✅ AI Core architecture (Runtime, Knowledge, Quality, Registry, Guardrails)
✅ Provider abstraction
✅ Model routing through AI Runtime
✅ LangChain + LangGraph + LangSmith as the core AI framework
✅ Groq and OpenRouter as the initial LLM providers
✅ Qdrant as the vector database
✅ PostgreSQL + Valkey as the operational data layer
✅ Evaluation-first and observability-first development
✅ Milestone engineering workflow
✅ Repository boundaries and separation of concerns
