# ADR-026: Model Routing Platform

## Status

Accepted

---

## Date

2026-07-17

---

## Context

ResearchMind has evolved from a traditional RAG system into a multi-provider AI platform supporting:

- OpenAI
- Anthropic Claude
- Google Gemini
- Groq
- Ollama

The current Generation Platform requires callers to manually specify providers and models:

```python
GenerationRequest(
    provider=GenerationProvider.OPENAI,
    model="gpt-5",
)
```

This approach becomes problematic as the system moves toward agentic workflows.

Upcoming systems such as:

- Research Runtime
- Planner Agents
- Reviewer Agents
- Validation Agents
- Artifact Generation Agents
- Multi-Agent Workflows

all require different model characteristics.

Examples:

| Task | Preferred Characteristics |
|-------|---------------------------|
| Planning | Strong reasoning |
| Validation | Cheap + structured |
| Summarization | Fast + inexpensive |
| Review | High quality reasoning |
| Large report generation | Long context |

Embedding model decisions inside agents would result in:

- duplicated logic
- provider lock-in
- difficult experimentation
- difficult cost optimization
- poor observability

A centralized routing mechanism is therefore required.

---

# Decision

Introduce a dedicated **Model Routing Platform** inside the Generation Platform.

Architecture:

```text
Generation Request
        ↓
Routing Platform
        ↓
Provider Selection
        ↓
Generation Service
```

Routing becomes the intelligence layer responsible for deciding:

- which model should be used
- which provider should be used
- which fallback models should be used
- how costs should be optimized
- how task-specific routing should be performed

---

# Why "Routing Platform" instead of "Model Selection Platform"?

Although the current responsibility is model routing, future requirements extend beyond simple model selection.

Routing will eventually include:

- model routing
- provider routing
- prompt routing
- validation routing
- tool routing
- memory routing
- workflow routing

Therefore:

```text
Routing Platform
```

is considered the broader and more future-proof abstraction.

---

# Decision Drivers

## 1. Agent Abstraction

Agents should think in terms of:

```text
Summarize this
Review this
Plan this
Validate this
```

rather than:

```text
Use Claude Sonnet
Use GPT5
```

Model decisions should remain infrastructure concerns.

---

## 2. Centralized Intelligence

Routing decisions should exist in a single location.

This avoids:

```python
if reasoning:
    use_claude()

if validation:
    use_gpt5_mini()
```

being duplicated across the codebase.

---

## 3. Cost Optimization

Different tasks require different cost profiles.

Examples:

| Task | Suggested Models |
|-------|------------------|
| Validation | GPT5 Nano |
| Summarization | Gemini Flash |
| Planning | Claude Sonnet |
| Long Context | Gemini Pro |

Routing enables intelligent cost allocation.

---

## 4. Future Agent Runtime

Upcoming Planner and Reviewer agents will heavily depend on routing.

The routing platform becomes foundational infrastructure for:

- Agent Runtime
- Research Runtime
- Multi-Agent Workflows

---

# Scope

Routing Platform responsibilities:

## Included

- model selection
- provider selection
- capability matching
- task routing
- cost optimization
- fallback chains
- observability metadata
- routing explanations

## Not Included

- prompt construction
- workflow execution
- tool execution
- validation execution
- experimentation policies
- generation itself

---

# Consequences

## Positive

### Centralized decision making

All model selection logic exists in one place.

---

### Better maintainability

Changing model preferences requires modifications in a single location.

---

### Better observability

Routing decisions can be traced and analyzed.

---

### Cost control

Tasks can automatically use cheaper models where appropriate.

---

### Future-proofing

Supports future:

- planners
- reviewers
- MCP integration
- adaptive routing

---

## Negative

### Additional complexity

A routing layer introduces another abstraction.

---

### Metadata maintenance

Model metadata must be periodically updated.

---

# Alternatives Considered

---

## Alternative 1

### Manual Provider Selection

Example:

```python
provider = OPENAI
```

### Rejected

Reason:

- duplicated logic
- difficult maintenance
- poor agent abstraction

---

## Alternative 2

### Agents Select Models Directly

Example:

```python
planner → claude
validator → gpt
```

### Rejected

Reason:

Agents should remain task-oriented.

---

## Alternative 3

### Dynamic ML-Based Router

### Rejected (for now)

Reason:

Premature complexity.

May be introduced later.

---

# Future Extensions

Possible future enhancements:

- adaptive routing
- evaluation driven routing
- budget-aware routing
- latency-aware routing
- A/B experimentation
- model ensembles
- enterprise privacy routing
- local model routing

---

# Related Documents

- Generation Platform Architecture
- Research Runtime Architecture
- Agent Runtime Architecture
