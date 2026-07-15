# ADR-024: Generation Platform Model Strategy

Status: Accepted

Date: 2026-07-15

---

# Context

ResearchMind aims to become an AI research platform supporting:

- RAG workflows
- Deep Research workflows
- Agentic systems
- MCP integrations
- Benchmarking
- Experimentation

The Generation Platform must therefore support multiple LLM providers and
multiple model capabilities.

The platform should not optimize solely for benchmark rankings.

Instead, it should optimize for:

- Quality
- Cost
- Latency
- Privacy
- Capability diversity
- Experimentation

---

# Decision

ResearchMind adopts a multi-provider model strategy.

Providers:

- OpenAI
- Anthropic Claude
- Google Gemini
- Groq
- Ollama

Each provider serves different workloads.

---

# Architectural Principles

## 1. Capability Diversity Over Leaderboards

The platform intentionally avoids selecting only the highest benchmark
models.

Different workloads require different capabilities.

Examples:

| Workload | Requirement |
|-----------|-------------|
| Query decomposition | Low cost + fast reasoning |
| Research synthesis | High quality reasoning |
| Agent execution | Tool calling |
| Internal documents | Privacy |
| Batch evaluation | Low cost |

No single model is optimal for every workload.

---

## 2. Provider Independence

Provider SDKs remain implementation details.

The platform exposes canonical generation models and provider interfaces.

All provider selection must happen through routing strategies.

---

## 3. Future Routing Support

Provider metadata must support:

- Cost-aware routing
- Capability-aware routing
- Latency-aware routing
- Privacy-aware routing
- Benchmark-driven routing

---

# Selected Models

---

# OpenAI

Purpose:

- Agent workflows
- Structured outputs
- High quality reasoning

Models:

## Primary

gpt-5

Use cases:

- Research synthesis
- Planner agents
- Report generation

## Secondary

gpt-5-mini

Use cases:

- Tool calling
- Agent execution

## Cost Optimized

gpt-5-nano

Use cases:

- Classification
- Query decomposition
- Metadata extraction

---

# Claude

Purpose:

- Writing quality
- Long-form synthesis
- Deep research

Models:

## Primary

claude-sonnet-4

Use cases:

- Final report generation
- Multi-document synthesis

## Future Benchmark Model

claude-opus-4

Use cases:

- Quality benchmarking

---

# Gemini

Purpose:

- Large context processing
- Cost optimization

Models:

## Primary

gemini-2.5-pro

Use cases:

- Notebook workflows
- Long-context reasoning

## Secondary

gemini-2.5-flash

Use cases:

- Query decomposition
- Fast summarization

---

# Groq

Purpose:

- Low latency inference

Models:

## Primary

llama-3.3-70b-versatile

Use cases:

- Interactive chat
- Fast retrieval QA

## Experimental

deepseek-r1-distill-llama-70b

Use cases:

- Reasoning experiments

---

# Ollama

Purpose:

- Privacy
- Local experimentation
- Offline execution

Models:

## Primary

qwen3:latest

Use cases:

- Local assistants
- Internal document analysis

## Reasoning

deepseek-r1

Use cases:

- Research experiments

## Coding

deepseek-coder-v2

Use cases:

- Code generation agents

## Lightweight

phi4

Use cases:

- Low-resource environments

---

# Routing Philosophy

ResearchMind will support:

- MANUAL
- CHEAPEST
- FASTEST
- QUALITY
- PRIVACY
- AUTO

Routing should use provider capabilities rather than hardcoded model names.

---

# Provider Capabilities

Each provider configuration should expose:

- context_window
- tool_calling
- reasoning
- vision
- streaming
- structured_output
- json_mode

Future routing decisions should rely on these capabilities.

---

# Cost Tracking

Generation statistics must include:

- prompt tokens
- completion tokens
- estimated cost
- latency

to support:

- observability
- benchmarking
- quality-per-dollar evaluations

---

# Consequences

Positive:

- Enables experimentation
- Supports future routing
- Avoids provider lock-in
- Enables benchmark evaluations
- Supports privacy requirements

Negative:

- Increased maintenance complexity
- Requires provider capability tracking
- Requires model catalog updates

---

# Future Work

Phase 3.6

Model Routing Platform

Phase 3.11

Benchmarking and observability integrations

Phase 4

Research Runtime and Agent workflows

Phase 5+

Automatic routing based on benchmark results.
