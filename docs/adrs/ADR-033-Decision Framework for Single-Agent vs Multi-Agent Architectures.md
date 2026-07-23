# ADR-033: Decision Framework for Single-Agent vs Multi-Agent Architectures

- **Status:** Accepted
- **Date:** 2026-07-20
- **Authors:** ResearchMind AI
- **Decision Type:** Strategic Architecture Decision
- **Supersedes:** None
- **Related ADRs:**
  - ADR-026 — Routing Platform
  - ADR-027 — Runtime Caching Platform
  - ADR-028 — Streaming Platform
  - ADR-029 — Memory Platform
  - ADR-031 — Research Runtime Architecture
  - ADR-032 — LangGraph Checkpointing Architecture

---

# Context

The AI ecosystem is increasingly adopting multi-agent architectures and agent frameworks such as:

- LangGraph multi-agent patterns
- CrewAI
- AutoGen
- OpenAI Agents SDK
- Semantic Kernel Agents

However, many projects introduce multiple agents primarily because the approach is popular rather than because it is required by the product or business problem.

This frequently results in:

- unnecessary complexity
- higher infrastructure costs
- increased latency
- difficult debugging
- poor observability
- difficult evaluation
- reduced reliability

ResearchMind is currently implementing a production-grade Deep Research Runtime based on a single orchestrated workflow consisting of:

```text
Goal
 ↓
Planning
 ↓
Decomposition
 ↓
Parallel Research
 ↓
Evidence Aggregation
 ↓
Review
 ↓
Synthesis
 ↓
Report
```

The question is whether future capabilities should continue evolving this architecture or transition toward multiple collaborating agents.

This ADR defines the architectural decision framework.

---

# Decision

ResearchMind will adopt the following principle:

> Prefer the simplest architecture capable of delivering the required business value.

And:

> Multi-agent systems are an optimization for specific coordination problems, not a default architecture.

And:

> Additional agents must justify their existence through measurable improvements in capability, quality, specialization, or organizational mapping.

---

# Decision Summary

ResearchMind will:

### Prefer:

```text
Single-Agent Runtime
```

until measurable constraints justify expansion.

### Introduce Multi-Agent Architectures only when:

- independent expertise is required;
- different tools or data sources are required;
- multiple autonomous workflows naturally exist;
- business value clearly exceeds complexity costs.

---

# Architectural Principles

---

# Principle 1

## Business value drives architecture.

Architecture evolution:

```text
Business Problem
        ↓
User Value
        ↓
Workflow
        ↓
Architecture
        ↓
Framework
```

Never:

```text
Framework
        ↓
Architecture
        ↓
Find use cases afterwards
```

---

# Principle 2

## Multi-agent is not a maturity indicator.

A multi-agent system is not inherently better.

A well-designed single-agent workflow can often outperform a poorly designed multi-agent system.

Engineering maturity is determined by:

- reliability
- observability
- evaluation
- maintainability
- business outcomes

rather than the number of agents.

---

# Principle 3

## Introduce complexity incrementally.

The recommended evolution path is:

```text
Single Workflow
        ↓
Single-Agent Runtime
        ↓
Tool-Augmented Runtime
        ↓
Supervisor + Specialized Agents
        ↓
Multi-Agent Organization
```

---

# Decision Criteria

---

# 1. Business Value

Question:

```text
What additional user value does another agent create?
```

Valid reasons:

- independent verification
- domain specialization
- autonomous monitoring
- organizational workflows
- cross-domain investigations

Invalid reasons:

- agents are trendy
- competitors use agents
- frameworks make it easy

---

# 2. Workflow Complexity

Question:

```text
Can a single workflow solve the problem?
```

If yes:

```text
Prefer Single-Agent
```

If work naturally decomposes into multiple independent responsibilities:

```text
Consider Multi-Agent
```

Example:

```text
Research
Patent Analysis
Financial Analysis
Compliance Analysis
```

---

# 3. Domain Specialization

Question:

```text
Do different parts of the workflow require different expertise?
```

Examples:

### Single-Agent

```text
Summarize research papers.
```

### Multi-Agent Candidate

```text
Perform acquisition due diligence.
```

Potential agents:

- Legal Agent
- Finance Agent
- Security Agent
- Market Agent

---

# 4. Tool Isolation

Question:

```text
Do different workflows require different tools?
```

Example:

```text
Academic Agent
    ↓
Arxiv / PubMed

Financial Agent
    ↓
SEC Filings

Legal Agent
    ↓
Legal Databases
```

Tool specialization can justify separate agents.

---

# 5. Organizational Mapping

Question:

```text
Would multiple humans naturally perform this work?
```

Example:

### Single Human

```text
Research PEFT methods.
```

### Multiple Humans

```text
Perform enterprise acquisition due diligence.
```

This naturally maps to multiple experts.

---

# Real-World Constraints

---

# Constraint 1 — Cost

Single-agent systems generally require fewer model invocations.

Example:

```text
Single Agent
10–20 LLM calls

Multi-Agent
50–200+ LLM calls
```

Multi-agent systems significantly increase inference cost.

---

# Constraint 2 — Latency

Single-agent:

```text
1–3 minutes
```

Multi-agent:

```text
5–20+ minutes
```

Long-running systems may negatively impact user experience.

---

# Constraint 3 — Reliability

Failure surface increases dramatically.

Single-agent:

```text
One graph
```

Multi-agent:

```text
Multiple graphs
+ coordination
+ communication
+ synchronization
```

---

# Constraint 4 — Evaluation Complexity

Single-agent:

```text
Evaluate output quality.
```

Multi-agent:

```text
Evaluate:

Planner
Researcher
Reviewer
Supervisor
Communication
Coordination
```

Evaluation becomes substantially harder.

---

# Constraint 5 — Observability Complexity

Multi-agent systems require:

- distributed traces
- agent communication logs
- shared memory inspection
- cost attribution
- event lineage

Operational complexity increases significantly.

---

# Constraint 6 — State Explosion

Single-agent:

```python
ResearchState
```

Multi-agent:

```python
PlannerState
ResearchState
ReviewerState
SupervisorState
SharedState
```

State management becomes substantially more difficult.

---

# Constraint 7 — Product Complexity

Users typically care about:

- answer quality
- reliability
- speed

Users rarely care about:

```text
How many agents produced the answer.
```

---

# Decision Matrix

| Question | Single-Agent | Multi-Agent |
|-----------|--------------|-------------|
| One workflow sufficient? | ✅ | ❌ |
| Independent expertise required? | ❌ | ✅ |
| Different tools required? | ❌ | ✅ |
| Human organizational mapping exists? | ❌ | ✅ |
| Cost sensitivity high? | ✅ | ❌ |
| Low latency important? | ✅ | ❌ |
| Easy debugging required? | ✅ | ❌ |
| Evaluation maturity low? | ✅ | ❌ |
| Product still evolving? | ✅ | ❌ |
| Enterprise workflows needed? | ❌ | ✅ |

---

# ResearchMind Decision

Current ResearchMind capabilities:

```text
Planning
Decomposition
Parallel Research
Evidence Aggregation
Review
Repair
Report Generation
```

This architecture already delivers most required value.

Current business requirements do NOT justify multiple agents.

Therefore:

```text
ResearchMind v1
=
Single-Agent Runtime
```

---

# Future Evolution Criteria

ResearchMind may consider multi-agent expansion when requirements such as the following emerge.

---

# Use Case 1

## Cross-Domain Research

Example:

```text
Research autonomous vehicles in China.
```

This may require:

- Academic Agent
- Financial Agent
- Patent Agent
- Market Agent

---

# Use Case 2

## Enterprise Intelligence

Example:

```text
Legal
Security
Compliance
Market Intelligence
```

---

# Use Case 3

## Autonomous Monitoring

Example:

```text
Monitor industries continuously.

Trigger investigations.

Update reports automatically.
```

---

# Use Case 4

## Manus-Style Autonomous Workflows

Large autonomous workflows may eventually require:

- Supervisor Agent
- Specialized Workers
- Reviewer Agent

---

# Recommended Evolution Path

```text
Phase 1
Single-Agent Runtime
```

↓

```text
Phase 2
Deep Research Product
```

↓

```text
Phase 3
MCP Platform
```

↓

```text
Phase 4
Enterprise Platform
```

↓

```text
Phase 5
Supervisor + Reviewer Agents
```

↓

```text
Phase 6
Specialized Domain Agents
```

↓

```text
Phase 7
Autonomous Research Organization
```

---

# Preconditions Before Multi-Agent Adoption

ResearchMind should NOT introduce multi-agent architectures until the following exist:

- mature observability
- evaluation platform
- lifecycle management
- cost monitoring
- event replay
- checkpointing
- human approval flows
- enterprise requirements

---

# Multi-Agent Adoption Rule

ResearchMind may adopt multi-agent architectures only if ALL of the following are true:

```text
1. One workflow is insufficient.

2. Independent expertise is required.

3. Agents can work semi-independently.

4. Additional value exceeds complexity.

5. Observability exists.

6. Evaluation exists.

7. Cost increase is acceptable.
```

If any of these conditions are not met:

```text
Prefer Single-Agent Runtime.
```

---

# Consequences

## Positive

- lower operational complexity
- lower infrastructure cost
- easier debugging
- simpler evaluation
- higher reliability
- faster iteration
- better product focus

---

## Negative

- less specialization
- reduced autonomy
- may limit future enterprise workflows
- eventual refactoring may be required

---

# Final Principle

> Multi-agent systems are not a sign of engineering maturity.

> Choosing the simplest architecture that maximizes business value is.

---

# Status

Accepted.

ResearchMind will continue evolving its Deep Research Runtime as a single-agent system until measurable business requirements justify multi-agent expansion.
