# ResearchMind — Guardrails Platform Integration PRD

**Document Version:** 2.1
**Platform:** Guardrails Platform Integration
**Milestone:** 3.9
**Status:** Ready for Implementation
**Owner:** ResearchMind Core Platform

---

# 1. Overview

## Purpose

The Guardrails Platform itself is already implemented.

This milestone focuses exclusively on integrating the existing Guardrails Platform into ResearchMind execution pipelines.

This milestone must **not** introduce duplicate implementations of:

- Guardrail models
- Guardrail interfaces
- Guardrail registries
- Guardrail services
- Policies
- Risk scoring
- Source trust platform
- Existing guardrail checks

The objective is to make Guardrails a first-class runtime component across Retrieval, Generation, and future Agent runtimes.

---

# 2. Problem Statement

Current execution flow:

```text
Request
    ↓
Generation
    ↓
Validation
```

Target execution flow:

```text
Request
    ↓
Input Guardrails
    ↓
Retrieval
    ↓
Retrieval Guardrails
    ↓
Context Building
    ↓
Generation
    ↓
Generation Guardrails
    ↓
Validation
    ↓
Runtime Guardrails
```

The Guardrails Platform already exists but is not fully integrated into runtime execution paths.

---

# 3. Existing Implementation

The following components already exist and must be reused.

## Core Infrastructure

- Guardrail models
- Guardrail enums
- Guardrail interfaces
- Guardrail registry
- Guardrail service
- Policies
- Risk scoring
- Artifact foundations

---

## Input Guardrails

- Prompt Injection Detection
- Scope Validation
- PII Detection
- Toxicity Detection
- Rate Limiting

---

## Retrieval Guardrails

- Context Sanitization
- Source Trust
- Citation Integrity
- Access Control

---

## Generation Guardrails

- Faithfulness
- Schema Enforcement
- PII Leakage
- Moderation

---

## Runtime Guardrails

- Budget Guardrails
- Loop Detection
- Tool Policies

---

# 4. Goals

## Primary Goals

### Generation Integration

Integrate `GuardrailService` into `GenerationService`.

### Retrieval Integration

Execute retrieval guardrails before prompt context construction.

### Runtime Integration Foundation

Expose integration points for future runtimes.

### Observability

Persist guardrail reports and expose metrics.

---

# 5. Non Goals

This milestone MUST NOT:

- Reimplement Guardrails Platform
- Create duplicate registries
- Create duplicate interfaces
- Create duplicate services
- Introduce new architectural abstractions
- Duplicate validation logic
- Rebuild source trust platform
- Rebuild runtime guardrails

---

# 6. Target Architecture

```text
User
 ↓
Input Guardrails
 ↓
Retrieval
 ↓
Retrieval Guardrails
 ↓
Context Builder
 ↓
Generation
 ↓
Generation Guardrails
 ↓
Validation
 ↓
Runtime Guardrails
```

---

# 7. Generation Integration

## Dependency Injection

Inject:

```python
GuardrailService
```

into:

```python
GenerationService
```

---

## Input Guardrails

Execute before provider invocation.

### Flow

```text
GenerationRequest
        ↓
evaluate_input()
        ↓
Provider
```

### Responsibilities

- Prompt Injection Detection
- Scope Validation
- PII Detection
- Toxicity Detection
- Rate Limiting

### Blocking Behaviour

If blocked:

```python
raise GuardrailViolationError(...)
```

Generation execution terminates immediately.

---

## Generation Guardrails

Execute immediately after provider generation and before validation.

### Flow

```text
Provider Result
        ↓
evaluate_generation()
        ↓
ValidationService
```

### Responsibilities

- Faithfulness checks
- Schema checks
- PII leakage checks
- Moderation checks

---

## Proposed Generation Flow

```text
Request
 ↓
Input Guardrails
 ↓
Provider
 ↓
Generation Guardrails
 ↓
Validation
 ↓
Result
```

---

# 8. Retrieval Integration

Execute after retrieval and before context building.

### Flow

```text
Retrieved Chunks
        ↓
evaluate_retrieval()
        ↓
Context Builder
```

### Responsibilities

- Context Sanitization
- Source Trust
- Citation Integrity
- Access Control

### Blocking Behaviour

Blocked retrieval must stop downstream generation.

---

# 9. Runtime Integration

No new runtime guardrails are required.

Future runtimes should consume:

```python
evaluate_runtime(
    execution_state,
    budget_policy,
)
```

## Future Consumers

- Research Runtime
- Planner Runtime
- Reviewer Runtime
- Agent Runtime
- MCP Runtime

No runtime should bypass Guardrails.

---

# 10. Generation Result Changes

Extend:

```python
GenerationResult
```

with:

```python
guardrails: GuardrailReport | None = None
```

Purpose:

- Debugging
- Observability
- Evaluations
- Artifacts
- Runtime decisions

---

# 11. Artifact Integration

## Initial Structure

```text
artifacts/
└── guardrails/
    └── {run_id}/
        └── report.json
```

---

## Future Structure

```text
artifacts/
└── guardrails/
    └── {run_id}/
        ├── input.json
        ├── retrieval.json
        ├── generation.json
        ├── runtime.json
        └── report.json
```

---

# 12. Observability

## Metrics

```text
guardrail_checks_total
guardrail_failures_total
guardrail_blocks_total
prompt_injection_attempts
pii_detections
policy_violations
overall_risk
```

---

## Events

```text
guardrails.started
guardrails.completed
guardrails.blocked
guardrails.failed
```

---

# 13. Execution Flows

## Generation Pipeline

```text
Request
 ↓
Input Guardrails
 ↓
Provider
 ↓
Generation Guardrails
 ↓
Validation
 ↓
Result
```

---

## Research Runtime Pipeline

```text
Request
 ↓
Input Guardrails
 ↓
Retrieval
 ↓
Retrieval Guardrails
 ↓
Context Builder
 ↓
Generation
 ↓
Generation Guardrails
 ↓
Validation
 ↓
Runtime Guardrails
```

---

# 14. Implementation Plan

## Phase 1 — Generation Integration

Tasks:

- Inject `GuardrailService`
- Execute `evaluate_input()`
- Execute `evaluate_generation()`
- Attach `GuardrailReport`

---

## Phase 2 — Retrieval Integration

Tasks:

- Execute `evaluate_retrieval()`
- Block unsafe contexts

---

## Phase 3 — Artifact Integration

Tasks:

- Persist reports
- Expose guardrail metadata

---

## Phase 4 — Observability

Tasks:

- Metrics
- Tracing
- Dashboards

---

## Phase 5 — Runtime Consumers

Future only.

No implementation required.

---

# 15. Acceptance Criteria

- Input guardrails execute automatically
- Retrieval guardrails execute automatically
- Generation guardrails execute automatically
- Runtime integration points exist
- Guardrail reports are persisted
- Metrics are emitted
- No duplicate implementations are introduced

---

# 16. Definition of Done

ResearchMind execution becomes:

```text
Safe Request
        ↓
Safe Retrieval
        ↓
Safe Context
        ↓
Safe Generation
        ↓
Valid Output
        ↓
Future Runtime Consumption
```

---

# Platform Responsibilities

## Guardrails Platform

Responsible for:

```text
Security
Policy Enforcement
Trust
Risk Management
```

---

## Validation Platform

Responsible for:

```text
Correctness
Quality
Faithfulness
Runtime Correctness
```

Both platforms remain independent and complementary.
