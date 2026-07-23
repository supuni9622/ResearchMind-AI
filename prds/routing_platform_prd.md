# Routing Platform PRD
Version: 1.0
Status: Approved
Owner: ResearchMind AI Runtime Platform
Phase: 3.x Generation Platform
Priority: High
Implementation Target: Before Research Runtime & Agent Runtime

---

# 1. Overview

The Routing Platform is responsible for intelligent model and provider selection across the entire AI Runtime.

It acts as the decision layer between:

- Planners
- Agents
- Runtime Services
- Generation Platform

and actual LLM providers.

The Routing Platform answers:

```text
Which model should execute this task?
Why was it selected?
What are the fallback models?
What provider should be used?
```

---

# 2. Motivation

ResearchMind is evolving from:

```text
Knowledge Platform
        ↓
RAG System
        ↓
Research Runtime
        ↓
Agent Runtime
```

As agents become more autonomous, hardcoded provider selection becomes impossible.

Different workloads require different models.

Examples:

| Task | Best Characteristics |
|------|----------------------|
| Planning | Strong reasoning |
| Validation | Cheap + structured |
| Summarization | Fast + cheap |
| Research | Long context + reasoning |
| Review | High quality |

Embedding model decisions inside agents would create:

- duplicated logic
- vendor lock-in
- difficult experimentation
- difficult optimization
- poor observability

A centralized routing layer becomes mandatory.

---

# 3. Goals

---

## Functional Goals

### G1

Intelligent model selection.

---

### G2

Provider abstraction.

---

### G3

Task based routing.

---

### G4

Cost optimization.

---

### G5

Fallback model selection.

---

### G6

Routing observability.

---

### G7

Future support for:

- adaptive routing
- A/B experiments
- multi-model agents
- enterprise privacy routing

---

# 4. Non Goals

The Routing Platform DOES NOT:

- execute prompts
- perform generation
- execute workflows
- execute tools
- perform validation
- manage prompts

Routing only decides.

---

# 5. Architecture Position

```text
Planner
Agents
Research Runtime
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

# 6. High Level Architecture

```text
Generation Request
        ↓
Routing Service
        ↓
Capability Filtering
        ↓
Policy Filtering
        ↓
Strategy Resolution
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

# 7. Why Routing Platform?

Alternative considered:

```text
Model Selection Platform
```

Rejected.

Future routing responsibilities:

- model routing
- provider routing
- prompt routing
- tool routing
- memory routing
- validation routing

Routing is the broader abstraction.

---

# 8. Core Concepts

---

# 8.1 Model Catalog

The Catalog Platform answers:

```text
What models exist?
```

Responsibilities:

- metadata storage
- capability definitions
- pricing information
- scoring information
- provider grouping

---

# 8.2 Routing Platform

The Routing Platform answers:

```text
Which model should be used?
```

Responsibilities:

- filtering
- scoring
- provider selection
- fallback generation

---

# 9. Package Structure

```text
app/
└── ai/
    └── runtime/
        └── generation/

            ├── catalog/
            │
            │   ├── models.py
            │   └── registry.py
            │

            └── routing/

                ├── enums.py
                ├── models.py
                ├── interfaces.py
                ├── service.py
                ├── create.py

                ├── scoring/
                │
                │   ├── interfaces.py
                │   ├── service.py
                │   └── weights.py
                │

                └── strategies/

                    ├── planning.py
                    ├── summarization.py
                    ├── review.py
                    ├── validation.py
                    ├── coding.py
                    └── research.py
```

---

# 10. Catalog Platform

---

# 10.1 ModelMetadata

```python
class ModelMetadata(BaseModel):

    provider: GenerationProvider

    model_name: str

    display_name: str

    context_window: int

    capabilities: ProviderCapabilities

    cost_per_input_1m: float

    cost_per_output_1m: float

    average_latency_ms: int | None

    quality_score: float

    reasoning_score: float

    coding_score: float

    summarization_score: float

    classification_score: float

    extraction_score: float

    planning_score: float

    review_score: float

    speed_score: float

    reliability_score: float

    priority: int = 100

    enabled: bool = True

    experimental: bool = False

    local: bool = False
```

---

# 10.2 Why Scores?

Future agents think in tasks.

Example:

Planner:

```text
Need planning capability.
```

NOT:

```text
Need Claude Sonnet.
```

Scores allow routing to remain model agnostic.

---

# 11. Models

Initial supported models.

---

## OpenAI

### GPT-5

Use cases:

- reasoning
- review
- coding
- structured outputs

---

### GPT-5 Mini

Use cases:

- summarization
- extraction
- validation

---

### GPT-5 Nano

Use cases:

- cheap classification
- validation
- lightweight tasks

---

## Claude

### Claude Sonnet 4

Primary model for:

- planning
- research
- review

---

### Claude Opus 4

Premium quality model.

Used for:

- difficult reasoning
- enterprise research

---

## Gemini

### Gemini 2.5 Pro

Primary long context model.

---

### Gemini Flash

Primary summarization model.

---

## Groq Models

### Llama 3.3 70B

Cheap + fast generation.

---

### DeepSeek R1 Distill

Cheap reasoning.

---

## Ollama Models

### Qwen3
### DeepSeek R1
### Phi4

Currently:

```text
registered
but disabled
```

Future:

- enterprise
- privacy mode
- offline deployments

---

# 12. Routing Strategies

```python
class RoutingStrategy(StrEnum):

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

# 13. Why Task Based Routing?

Agent Runtime operates using tasks.

Examples:

| Agent | Strategy |
|--------|-----------|
| Planner | PLANNING |
| Reviewer | REVIEW |
| Validator | VALIDATION |
| Summarizer | SUMMARIZATION |
| Research Agent | REASONING |

---

# 14. Routing Flow

---

# Step 1

Capability Filtering.

Remove models that do not support:

- structured outputs
- tools
- streaming
- vision
- required context window

---

# Step 2

Policy Filtering.

Remove:

- disabled models
- experimental models
- local models

unless explicitly requested.

---

# Step 3

Resolve Routing Strategy.

Examples:

```text
Planning
Validation
Review
Research
```

---

# Step 4

Score models.

---

# Step 5

Select primary model.

---

# Step 6

Generate fallback chain.

---

# Step 7

Return routing decision.

---

# 15. Scoring Engine

Different strategies use different weights.

---

# Planning

```text
0.40 reasoning
0.30 planning
0.20 reliability
0.10 quality
```

---

# Validation

```text
0.35 speed
0.35 cost
0.20 structured output
0.10 reliability
```

---

# Summarization

```text
0.40 summarization
0.30 speed
0.20 cost
0.10 quality
```

---

# Review

```text
0.40 review
0.30 reasoning
0.20 quality
0.10 reliability
```

---

# Coding

```text
0.50 coding
0.20 reasoning
0.20 quality
0.10 reliability
```

---

# 16. Routing Decision

```python
class RoutingDecision(BaseModel):

    selected_model: ModelMetadata

    fallback_models: list[ModelMetadata]

    strategy: RoutingStrategy

    score: float

    reasons: list[str]
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
    "highest reasoning score",
    "supports long context"
  ]
}
```

---

# 17. Fallback Architecture

Fallbacks are mandatory.

Reasons:

- provider outages
- rate limits
- quotas
- timeouts
- transient failures

---

## Planning Route

```text
Primary:
Claude Sonnet 4

Fallback 1:
GPT5

Fallback 2:
Gemini Pro
```

---

## Summarization Route

```text
Primary:
Gemini Flash

Fallback:
GPT5 Mini

Fallback:
Llama 3.3
```

---

## Validation Route

```text
Primary:
GPT5 Nano

Fallback:
Gemini Flash
```

---

## Coding Route

```text
Primary:
GPT5

Fallback:
Claude Sonnet
```

---

# 18. Initial Route Recommendations

| Strategy | Primary | Fallback |
|-----------|----------|-----------|
| Planning | Claude Sonnet | GPT5 |
| Review | Claude Sonnet | GPT5 |
| Research | Claude Sonnet | Gemini Pro |
| Long Context | Gemini Pro | Claude Sonnet |
| Validation | GPT5 Nano | Gemini Flash |
| Summarization | Gemini Flash | GPT5 Mini |
| Coding | GPT5 | Claude Sonnet |
| Cheap | Llama 3.3 | Gemini Flash |
| Fast | Llama 3.3 | GPT5 Mini |

---

# 19. Integration with Generation Platform

Current:

```python
GenerationRequest(
    provider=OPENAI
)
```

Future:

```python
GenerationRequest(
    routing_strategy=PLANNING
)
```

or

```python
GenerationRequest(
    required_capabilities=[
        STRUCTURED_OUTPUT,
        TOOLS
    ]
)
```

Generation Service Flow:

```text
Request
    ↓
Routing Service
    ↓
Generation Provider
```

---

# 20. Integration with Agent Runtime

Planner:

```python
strategy=PLANNING
```

Reviewer:

```python
strategy=REVIEW
```

Validator:

```python
strategy=VALIDATION
```

Research Agent:

```python
strategy=REASONING
```

---

# 21. Observability

Every routing decision should be logged.

Example:

```json
{
    "request_id": "...",
    "strategy": "planning",
    "selected_model": "claude-sonnet-4",
    "fallbacks": [
        "gpt-5"
    ],
    "score": 9.3,
    "reasons": [
        "highest planning score"
    ],
    "latency_ms": 8
}
```

---

# 22. Future Evolution

---

# Phase 1

Static routing.

(Current implementation)

---

# Phase 2

Adaptive routing.

Use:

- latency metrics
- evaluation metrics
- quality metrics

---

# Phase 3

Experiment routing.

Examples:

```text
10% GPT5
90% Claude
```

---

# Phase 4

Budget aware routing.

```text
Budget exceeded
↓
Route to cheaper model
```

---

# Phase 5

Multi-model execution.

Examples:

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

# 23. Implementation Plan

---

## PR-1

Catalog Enhancements

- extend ModelMetadata
- add scores
- add enabled/local flags

---

## PR-2

Catalog Registry

- create registry
- helper methods
- lookup methods

---

## PR-3

Routing Models

- RoutingStrategy
- RoutingDecision
- RoutingRequest

---

## PR-4

Routing Service

- filtering
- scoring
- fallback generation

---

## PR-5

Generation Integration

GenerationService automatically routes models.

---

## PR-6

Observability

- logs
- metrics
- traces

---

# Success Criteria

✅ Generation requests no longer hardcode providers.

✅ Planner agents can select models using tasks.

✅ Automatic fallback chains exist.

✅ Routing decisions are observable.

✅ Cost optimized model usage.

✅ Foundation ready for Agent Runtime.
