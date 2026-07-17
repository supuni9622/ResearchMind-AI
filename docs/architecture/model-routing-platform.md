# Model Routing Platform

## Overview

The Model Routing Platform provides intelligent model selection for all AI workloads inside ResearchMind.

Its purpose is to determine:

1. Which model should be used
2. Which provider should be used
3. Which fallback models should be used
4. Why the decision was made

---

# Goals

## Functional Goals

- intelligent model selection
- provider abstraction
- task-based routing
- cost optimization
- fallback handling
- observability

---

## Non Functional Goals

- deterministic
- extensible
- provider agnostic
- explainable
- low latency

---

# Architecture Position

```text
Planner / Agents
         ↓
Generation Request
         ↓
Routing Platform
         ↓
Generation Platform
         ↓
Provider
```

---

# High Level Architecture

```text
Generation Request
        ↓
Routing Service
        ↓
Capability Filter
        ↓
Task Strategy Resolver
        ↓
Scoring Engine
        ↓
Fallback Builder
        ↓
Routing Decision
        ↓
Generation Service
```

---

# Main Components

---

# 1. Model Catalog

Purpose:

Provide metadata about available models.

Answers:

```text
What models exist?
What capabilities do they have?
What do they cost?
```

---

## Responsibilities

- model registry
- metadata storage
- capability definitions
- provider grouping

---

# ModelMetadata

```python
class ModelMetadata:
    provider
    model_name
    display_name
    context_window
    capabilities

    cost_per_input_1m
    cost_per_output_1m

    quality_score
    reasoning_score
    coding_score

    summarization_score
    classification_score
    extraction_score
    planning_score
    review_score

    speed_score
    reliability_score

    enabled
    experimental
    local
```

---

# Why Scores?

Future agents think in tasks.

Example:

Planner:

```text
Need planning capability.
```

instead of:

```text
Need Claude.
```

Scores allow routing decisions to remain model agnostic.

---

# Routing Strategies

```python
class RoutingStrategy:

    AUTO

    FAST

    CHEAP

    QUALITY

    REASONING

    CODING

    LONG_CONTEXT

    STRUCTURED_OUTPUT

    SUMMARIZATION

    CLASSIFICATION

    EXTRACTION

    VALIDATION

    PLANNING

    REVIEW

    LOCAL
```

---

# Why Task-Based Strategies?

Task-based strategies align with future agents.

Examples:

| Agent | Strategy |
|--------|-----------|
| Planner | PLANNING |
| Reviewer | REVIEW |
| Validator | VALIDATION |
| Summarizer | SUMMARIZATION |

---

# Routing Flow

---

# Step 1

## Capability Filtering

Remove models that cannot satisfy requirements.

Examples:

- tool calling
- structured output
- streaming
- vision
- context size

---

# Step 2

## Policy Filtering

Remove:

- disabled models
- experimental models
- local models (if not enabled)

---

# Step 3

## Strategy Resolution

Determine routing objective.

Examples:

```text
Planning
Validation
Research
Review
```

---

# Step 4

## Model Scoring

Example:

```text
score =
0.40 reasoning
0.30 quality
0.20 reliability
0.10 speed
```

Weights vary per strategy.

---

# Step 5

## Fallback Construction

Construct fallback chains.

Example:

```text
Claude Sonnet
        ↓
GPT5
        ↓
Gemini Pro
```

---

# Routing Decision

```python
class RoutingDecision:

    selected_model

    fallback_models

    strategy

    score

    reasons
```

---

# Example

```json
{
  "strategy": "planning",
  "selected_model": "claude-sonnet-4",
  "fallback_models": [
      "gpt-5",
      "gemini-2.5-pro"
  ],
  "reasons": [
      "highest planning score",
      "strong reasoning",
      "high reliability"
  ]
}
```

---

# Routing Pipeline

```text
Request
   ↓
Capability Filter
   ↓
Strategy Selection
   ↓
Model Scoring
   ↓
Primary Selection
   ↓
Fallback Builder
   ↓
Routing Decision
```

---

# Fallback Architecture

Fallbacks are mandatory.

Reasons:

- provider outages
- rate limits
- quota exhaustion
- timeouts
- transient failures

---

## Example

### Planning Route

```text
Primary:

Claude Sonnet 4

Fallback 1:

GPT5

Fallback 2:

Gemini Pro
```

---

### Validation Route

```text
Primary:

GPT5 Nano

Fallback:

Gemini Flash
```

---

### Summarization Route

```text
Primary:

Gemini Flash

Fallback:

GPT5 Mini

Fallback:

Llama 3.3
```

---

# Ollama Strategy

Current policy:

```text
Registered
But Disabled
```

Reasons:

- local models not yet production validated
- cloud providers currently offer superior quality

Future support:

- privacy mode
- enterprise deployments
- offline environments

---

# Cost Optimization

Routing should always prefer:

```text
Best quality model
within acceptable cost constraints
```

Examples:

| Task | Preferred Models |
|------|------------------|
| Validation | GPT5 Nano |
| Summarization | Gemini Flash |
| Planning | Claude Sonnet |
| Review | Claude Sonnet |
| Long Context | Gemini Pro |

---

# Observability

Every routing decision should be persisted.

Example:

```json
{
  "request_id": "...",
  "strategy": "planning",
  "selected_model": "claude-sonnet-4",
  "fallback_models": [
      "gpt-5"
  ],
  "reasons": [
      "highest planning score"
  ],
  "routing_latency_ms": 12
}
```

---

# Observability Benefits

- LangSmith traces
- cost analysis
- evaluation platform
- experiment analysis
- debugging
- planner explainability

---

# Future Evolution

---

# Phase 1

Static rule-based routing.

---

# Phase 2

Adaptive routing.

Examples:

- evaluation driven routing
- latency based routing
- budget based routing

---

# Phase 3

Experiment driven routing.

Examples:

```text
10% GPT5
90% Claude
```

---

# Phase 4

Multi-model ensembles.

Example:

```text
Planner
    ↓
Claude

Writer
    ↓
GPT5

Reviewer
    ↓
Gemini
```

---

# Proposed Package Structure

```text
generation/

├── catalog/
│
├── models.py
├── registry.py
│
├── routing/
│
├── enums.py
├── models.py
├── service.py
├── create.py
├── scoring/
└── strategies/
```

---

# Sequence Diagram

```text
Planner
    ↓
GenerationRequest
    ↓
RoutingService
    ↓
Catalog
    ↓
ScoringEngine
    ↓
RoutingDecision
    ↓
GenerationService
    ↓
Provider
```

---

# Summary

The Model Routing Platform becomes the central intelligence layer responsible for selecting the optimal model for every AI workload inside ResearchMind.

It provides:

- provider abstraction
- cost optimization
- task-aware routing
- explainability
- future agent compatibility
- production resiliency through fallback chains
