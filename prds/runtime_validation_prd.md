# Runtime Validation Platform PRD

Version: 1.0
Status: Planned
Phase: AI Runtime Platform → Validation Platform → Runtime Validation

---

# 1. Overview

The Runtime Validation Platform introduces a fourth validation stage into ResearchMind's Validation Platform.

Current validation pipeline:

```text
Input Validation
        ↓
Output Validation
        ↓
Hallucination Validation
```

New pipeline:

```text
Input Validation
        ↓
Output Validation
        ↓
Hallucination Validation
        ↓
Runtime Validation
```

Runtime Validation introduces semantic, workflow, and domain-level correctness guarantees that cannot be enforced through:

- JSON Schema
- Pydantic validation
- Citation validation
- Hallucination heuristics

Its purpose is to ensure generated outputs satisfy the requirements of the specific runtime consuming them.

---

# 2. Motivation

Current validation guarantees:

✅ Request validity

✅ Provider compatibility

✅ JSON correctness

✅ Schema correctness

✅ Citation correctness

✅ Groundedness heuristics

Missing guarantees:

❌ Output completeness

❌ Runtime-specific requirements

❌ Workflow consistency

❌ Semantic usefulness

❌ Business correctness

---

## Example

This response passes schema validation:

```json
{
  "summary": "AI is important."
}
```

However, it is unusable for the Research Runtime because:

- No citations
- No evidence
- No sections
- No confidence score

Runtime Validation closes this gap.

---

# 3. Goals

## Functional Goals

1. Support runtime-specific validators.
2. Introduce validation contracts.
3. Support multiple runtimes.
4. Integrate into ValidationReport.
5. Produce runtime quality scores.
6. Enable downstream quality gates.

---

## Non-Functional Goals

- Deterministic
- Provider-independent
- Async
- Extensible
- Observable
- Production ready

---

# 4. Design Principles

---

## Principle 1 — Runtime Specific

Validation requirements differ by runtime.

Examples:

- Chat Runtime
- Research Runtime
- Planner Runtime
- Reviewer Runtime
- Agent Runtime

---

## Principle 2 — Provider Independent

Validators must never depend on:

- OpenAI SDK
- Anthropic SDK
- LangChain providers

---

## Principle 3 — Deterministic

Runtime validation should avoid LLM calls.

Future LLM-based validation may be introduced separately.

---

## Principle 4 — Reuse Existing Models

Reuse:

```python
ValidationIssue
ValidationResult
ValidatorOutcome
ValidationReport
```

No duplicate models.

---

## Principle 5 — Extend Existing Architecture

Runtime Validation extends the existing Validation Platform.

It is not a separate platform.

---

# 5. Architecture

```text
Generation Result
        ↓
ValidationService
        ↓
Input Validators
        ↓
Output Validators
        ↓
Hallucination Validators
        ↓
Runtime Validators
        ↓
Validation Report
```

---

# 6. Folder Structure

```text
app/
└── ai/
    └── runtime/
        └── generation/
            └── validation/
                ├── create.py
                ├── interfaces.py
                ├── models.py
                ├── registry.py
                ├── service.py
                ├── scoring.py
                │
                ├── input/
                ├── output/
                │
                └── runtime/
                    ├── __init__.py
                    ├── interfaces.py
                    ├── registry.py
                    ├── service.py
                    │
                    ├── contracts/
                    │   ├── base.py
                    │   ├── research.py
                    │   ├── planner.py
                    │   ├── reviewer.py
                    │   ├── agent.py
                    │   └── mcp.py
                    │
                    ├── validators/
                    │   ├── completeness.py
                    │   ├── consistency.py
                    │   ├── confidence.py
                    │   ├── evidence.py
                    │   └── citation.py
                    │
                    └── tests/
```

---

# 7. Runtime Types

```python
class RuntimeType(StrEnum):

    CHAT = "chat"

    RESEARCH = "research"

    PLANNER = "planner"

    REVIEWER = "reviewer"

    AGENT = "agent"

    MCP = "mcp"
```

---

# 8. Core Concepts

---

# Runtime Contract

A contract defines what constitutes a valid output for a runtime.

Examples:

Research Runtime requires:

- sections
- citations
- confidence
- evidence

Planner Runtime requires:

- steps
- dependencies
- execution order

---

# Runtime Validator

Performs checks against runtime contracts.

---

# Runtime Validation Service

Coordinates execution of runtime validators.

---

# Runtime Registry

Supports dynamic validator registration.

---

# 9. Interfaces

---

## RuntimeValidatorInterface

```python
class RuntimeValidatorInterface(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def runtime(self) -> RuntimeType:
        pass

    @abstractmethod
    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:
        pass
```

---

## RuntimeContractInterface

```python
class RuntimeContractInterface(ABC):

    @property
    @abstractmethod
    def runtime(self) -> RuntimeType:
        pass

    @abstractmethod
    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:
        pass
```

---

# 10. Validation Registry Changes

Extend existing registry.

Current:

```python
_input_validators
_output_validators
_hallucination_validators
```

Add:

```python
_runtime_validators
```

Methods:

```python
register_runtime_validator()

runtime_validators
```

---

# 11. Validation Service Changes

---

## New Stage

```python
async def validate_runtime(
    self,
    result: GenerationResult,
) -> ValidationResult:
```

---

## Updated Validation Flow

```python
input_validation
        ↓
output_validation
        ↓
hallucination_validation
        ↓
runtime_validation
```

---

## ValidationReport

No model changes required.

Already supported:

```python
runtime_validation: ValidationResult | None
```

---

## Updated Report

```python
ValidationReport(
    input_validation=...
    output_validation=...
    hallucination_validation=...
    runtime_validation=...
    overall_score=...
    valid=...
)
```

---

# 12. Overall Score

`compute_overall_score()` already supports runtime scores.

No architectural changes required.

Current weights:

```python
input: 0.15
output: 0.35
hallucination: 0.30
runtime: 0.20
```

---

# 13. Runtime Resolution

Runtime validators execute only when applicable.

Example:

```python
request.runtime == RuntimeType.RESEARCH
```

Only research validators should execute.

---

# 14. Generic Runtime Validators

These validators are reusable.

---

## CompletenessValidator

Checks:

- empty summaries
- empty sections
- missing required fields
- trivial outputs

---

## ConsistencyValidator

Checks:

- orphan references
- invalid section references
- invalid evidence references

---

## ConfidenceValidator

Checks:

```text
0 <= confidence <= 1
```

---

## EvidenceValidator

Checks:

- evidence exists
- evidence references valid sources

---

## RuntimeCitationValidator

Checks:

- evidence references valid citations
- citations exist

---

# 15. Research Runtime Contract

This is the first implementation.

---

## Required Fields

### Summary

Must exist.

---

### Sections

Minimum:

```text
2 sections
```

---

### Citations

Minimum:

```text
1 citation
```

---

### Evidence

Minimum:

```text
1 evidence item
```

---

### Confidence

Required.

Range:

```text
0 → 1
```

---

### Minimum Length

Prevent trivial outputs.

---

## Example Errors

```text
Research result missing citations.

Research result missing evidence.

Research result incomplete.

Research result confidence missing.
```

---

# 16. Planner Runtime Contract

Future.

Checks:

- steps exist
- dependencies valid
- ordering valid
- no cycles

---

# 17. Reviewer Runtime Contract

Future.

Checks:

- criticisms exist
- missing areas identified
- confidence exists

---

# 18. Agent Runtime Contract

Future.

Checks:

- tool calls valid
- actions valid
- state transitions valid

---

# 19. MCP Runtime Contract

Future.

Checks:

- tool results exist
- tool failures handled
- capability references valid

---

# 20. Runtime Validation Severity

Most runtime contract failures should be:

```text
ERROR
```

Examples:

- missing citations
- missing evidence
- invalid workflow

Warnings:

- low confidence
- short summary
- insufficient detail

---

# 21. Validation Report Example

```json
{
  "runtime_validation": {
    "valid": false,
    "score": 0.42,
    "issues": [
      {
        "validator": "research_contract",
        "severity": "error",
        "message": "Research result contains no citations."
      }
    ]
  }
}
```

---

# 22. Metrics

Track:

```text
runtime_validation_duration_ms

runtime_validation_score

runtime_validation_failures

runtime_validator_failures

runtime_contract_failures
```

---

# 23. Observability Events

```text
runtime.validation.started

runtime.validation.completed

runtime.validation.failed
```

---

# 24. Integration Points

---

## Generation Platform

```text
Generation
      ↓
Validation
      ↓
Runtime Validation
      ↓
Artifacts
```

---

## Research Runtime

```text
Research Output
        ↓
Runtime Validation
        ↓
Quality Gate
```

---

## Evaluation Platform

Runtime scores become evaluation metrics.

---

## Agent Platform

Agents may use runtime validation as self-check mechanisms.

---

# 25. Testing Requirements

---

## Unit Tests

### Registry

- registration
- lookup

---

### Service

- stage execution
- score aggregation
- crash handling

---

### Validators

- completeness
- consistency
- confidence
- evidence

---

### Contracts

- success cases
- failure cases

---

## Integration Tests

```text
Generation
        ↓
Validation
        ↓
Runtime Validation
        ↓
Validation Report
```

---

# 26. Documentation Requirements

Update:

```text
validation_platform_prd.md

runtime_validation_prd.md

generation_platform_architecture.md

PROJECT_STATUS.md

ROADMAP.md
```

---

# 27. Future Extensions

---

## LLM Runtime Validators

Examples:

- answer quality scoring
- completeness scoring
- reviewer agents

---

## Runtime Quality Gates

Examples:

```text
score < 0.5

↓

automatic regeneration
```

---

## Self-Reflection

Agents may use runtime validation to improve outputs.

---

## Research Runtime

Runtime validation becomes a mandatory quality gate.

---

# 28. Acceptance Criteria

- [ ] Runtime validator architecture implemented
- [ ] Runtime registry implemented
- [ ] Runtime service implemented
- [ ] ValidationReport integration completed
- [ ] Research runtime contract implemented
- [ ] Metrics implemented
- [ ] Tests implemented
- [ ] Documentation completed

---

# 29. Definition of Done

ResearchMind can guarantee:

```text
Valid Input
        +
Valid Output
        +
Grounded Output
        +
Runtime Correctness
```

before any downstream runtime consumes generated outputs.

This becomes the final validation stage before:

- Artifacts
- Research Runtime
- Agent Runtime
- Evaluation Platform
- Human Review
