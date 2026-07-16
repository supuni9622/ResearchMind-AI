ResearchMind — Validation Platform PRD

Document Version: 1.0
Platform: Validation Platform
Milestone: 11.15
Status: Ready for Implementation
Owner: ResearchMind Core Platform
Target Builder: Claude Code

---

Implementation Status (as of 2026-07-16): A narrow slice of this PRD has
been implemented under `generation/validation/` (part of the Generation
Platform, not yet its own top-level platform) — Output Validation only,
scoped to schema (`SchemaValidator`, via `jsonschema`) and citation
(`CitationValidator`, fabricated-citation detection against retrieved
context) checks, wired into `GenerationService` as a post-processing
step. The Regeneration Policy concept (Section 16) is implemented
directly inside `GenerationService` (`max_regeneration_attempts`,
corrective-feedback retries) rather than as a Validation Platform
policy module.

Not implemented: Input Validation, Hallucination Validation, Runtime
Validators (per-runtime contracts), the Contracts layer, Scoring
system, `ValidationReport` (a single `ValidationResult` per generation
is used instead — no aggregated multi-stage report), and the standalone
`validation/` top-level folder structure described in Section 6 (the
current implementation lives inside `generation/validation/`, following
the Generation Platform's existing module layout rather than this PRD's
proposed independent platform structure). See
`docs/architecture/structured-output-platform.md` → "Validation
Platform Integration" for the current, continuously-updated state of
what exists today. This PRD remains the target design for when
Validation is promoted to a standalone, runtime-shared platform.

---

1. Overview
Purpose

The Validation Platform provides deterministic quality assurance and contract enforcement for all AI outputs produced inside ResearchMind.

It acts as the quality layer between:

Generation
        ↓
Validation
        ↓
Artifacts
        ↓
Evaluation

The platform ensures:

requests are valid
providers are compatible
outputs conform to schemas
citations are grounded
runtime contracts are satisfied
hallucinations are detected
downstream runtimes receive reliable objects
2. Vision

ResearchMind is platform-oriented.

Validation must become:

Reusable Capability

usable by:

Research Runtime
Chat Runtime
Planner Runtime
Reviewer Runtime
Agent Runtime
MCP Runtime
Future Multi-Agent Runtime
3. Goals
Primary Goals
Input Validation

Validate requests before generation.

Output Validation

Validate generated outputs.

Hallucination Detection

Detect unsupported claims.

Runtime Contract Validation

Validate runtime-specific outputs.

Validation Reports

Provide quality metadata to downstream systems.

Regeneration Support

Allow failed outputs to be regenerated.

Non Goals

Validation Platform DOES NOT own:

❌ Prompt Injection

❌ Jailbreak Detection

❌ PII Detection

❌ Secrets Detection

❌ Content Moderation

❌ LLM-as-a-Judge Evaluation

❌ Cost Evaluation

❌ Runtime Orchestration

These belong to:

Guardrails Platform
Evaluation Platform
Research Runtime
4. Architectural Principles
Principle 1

Platforms provide capabilities.

Runtimes orchestrate them.

Principle 2

Validation should remain deterministic.

Avoid expensive LLM calls.

Principle 3

Validation must never directly execute tools.

Principle 4

Validation failures should rarely raise exceptions.

Prefer:

ValidationResult
Principle 5

Validation should be extensible.

Future runtimes must integrate without modification.

5. Architecture
Input Request
        ↓
Input Validation
        ↓
Generation
        ↓
Structured Outputs
        ↓
Output Validation
        ↓
Hallucination Validation
        ↓
Runtime Validation
        ↓
Validation Report
        ↓
Artifacts
        ↓
Evaluation
6. Folder Structure
validation/

├── interfaces.py
├── models.py
├── enums.py
├── exceptions.py
├── registry.py
├── service.py
├── create.py
├── constants.py

├── input/
├── output/
├── hallucination/
├── runtime/
├── contracts/
├── policies/
├── scoring/
├── reports/
├── utils/
└── tests/
Detailed Structure
validation/

├── input/

│   ├── empty_prompt.py
│   ├── token_budget.py
│   ├── provider_limits.py
│   ├── request_schema.py
│   ├── context_validation.py
│   ├── prompt_variables.py
│   └── metadata_validation.py

├── output/

│   ├── json_validator.py
│   ├── schema_validator.py
│   ├── citation_validator.py
│   ├── completeness_validator.py
│   ├── consistency_validator.py
│   ├── response_size_validator.py
│   └── formatting_validator.py

├── hallucination/

│   ├── groundedness_validator.py
│   ├── unsupported_claim_validator.py
│   ├── contradiction_validator.py
│   ├── source_overlap_validator.py
│   ├── citation_coverage_validator.py
│   └── fact_consistency_validator.py

├── runtime/

│   ├── research/
│   ├── planner/
│   ├── reviewer/
│   ├── agent/
│   └── mcp/

├── contracts/

│   ├── research.py
│   ├── planner.py
│   ├── reviewer.py
│   ├── agent.py
│   ├── mcp.py
│   └── generation.py

├── scoring/

│   ├── groundedness.py
│   ├── completeness.py
│   ├── consistency.py
│   ├── confidence.py
│   └── validation_score.py

├── reports/

│   ├── validation_report.py
│   └── issue_report.py
7. Core Models
ValidationSeverity
INFO
WARNING
ERROR
CRITICAL
ValidationStage
INPUT
OUTPUT
HALLUCINATION
RUNTIME
RuntimeType
RESEARCH
PLANNER
REVIEWER
AGENT
MCP
ValidationIssue
class ValidationIssue:

    validator: str

    stage: ValidationStage

    severity: ValidationSeverity

    code: str

    message: str

    field: str | None

    metadata: dict
ValidationResult
class ValidationResult:

    valid: bool

    stage: ValidationStage

    score: float | None

    issues: list[ValidationIssue]

    metadata: dict
ValidationReport
class ValidationReport:

    input_validation

    output_validation

    hallucination_validation

    runtime_validation

    overall_score

    final_status
8. Input Validation
Empty Prompt Validator

Checks:

empty user prompt
empty system prompt
missing variables
Token Budget Validator

Checks:

estimated tokens
context overflow
provider limits

Uses:

Observability Platform
TokenCounter
Provider Limits Validator

Checks:

streaming support
structured output support
tool support
reasoning support
vision support
Request Schema Validator

Checks:

response format compatibility
output_model validity
output_schema validity
Context Validator

Checks:

empty chunks
duplicate chunks
metadata consistency
citation consistency
9. Output Validation
JSON Validator

Checks:

valid json
repairable json
parseability
Schema Validator

Checks:

jsonschema
pydantic schemas
required fields
Citation Validator

Checks:

citation existence
invalid references
duplicate references
Completeness Validator

Checks:

missing report sections
empty summaries
missing references
Consistency Validator

Checks:

internal contradictions
section mismatches
field conflicts
Formatting Validator

Checks:

markdown structure
invalid headings
table formatting
Response Size Validator

Checks:

minimum response size
maximum response size
empty outputs
10. Hallucination Validation
Purpose

Provide lightweight groundedness validation.

No LLM Judge.

Groundedness Validator

Checks:

generated facts overlap with sources

Produces:

groundedness score
Unsupported Claim Validator

Checks:

claims without citations
Citation Coverage Validator

Checks:

supported claims %
Contradiction Validator

Checks:

answer contradicts sources
Source Overlap Validator

Checks:

semantic similarity
Fact Consistency Validator

Checks:

entity mismatch
numbers mismatch
dates mismatch
Hallucination Score
0.0 -> hallucinated

1.0 -> fully grounded
11. Runtime Validators
Research Runtime

Checks:

summary exists
findings exist
references exist
limitations exist
minimum citations
Planner Runtime

Checks:

objective exists
steps exist
dependency correctness
tool validity
Reviewer Runtime

Checks:

review notes exist
score exists
recommendation exists
Agent Runtime

Checks:

tool names valid
tool args valid
budget limits
loop detection
state validity
MCP Runtime

Checks:

tool exists
permissions valid
payload schema valid
protocol compliance
12. Contracts Layer

Purpose:

Provide runtime requirements without hardcoding validators.

Example
Research Contract
ResearchContract:

    required_sections

    min_references

    min_findings

    require_limitations
Agent Contract
AgentContract:

    max_tool_calls

    max_depth

    max_cost

    allowed_tools
MCP Contract
MCPContract:

    allowed_tools

    require_permissions

    validate_payloads
13. Validation Registry

Purpose:

Dynamic validator registration.

ValidationRegistry

├── input_validators
├── output_validators
├── hallucination_validators
└── runtime_validators
Registry API
register_input_validator()

register_output_validator()

register_runtime_validator()

register_hallucination_validator()
14. Validation Service
Input
validate_input()
Output
validate_output()
Hallucination
validate_groundedness()
Runtime
validate_runtime()
Full Validation
validate()

Flow:

Input
↓
Output
↓
Hallucination
↓
Runtime
↓
Report
15. Scoring System

Each validator may optionally return:

score: float
Examples
Groundedness Score
Completeness Score
Consistency Score
Citation Score
Overall Formula
overall_score =
(
    input_score * 0.15 +
    output_score * 0.35 +
    hallucination_score * 0.30 +
    runtime_score * 0.20
)

Configurable.

16. Policies
Acceptance Policy
minimum_score
maximum_errors
maximum_warnings
Regeneration Policy

Used by Generation Platform.

if validation_failed:
    regenerate()
Fail Fast Policy

Some validations may stop generation.

Example:

invalid schema
missing provider capability
17. Integration Points
Generation Platform
Generation
↓
Validation
Structured Output Platform
parsed_output
↓
schema validation
Artifact Platform
Validation Report
↓
Artifacts
Evaluation Platform
Validation Report
↓
Evaluation Metrics
Observability Platform

Expose:

validation latency
validation failures
hallucination rates
runtime violations
18. Future Extensions
Phase 2
LLM Judge Validators
faithfulness
quality
reasoning correctness
Phase 3
Streaming Validation
incremental validation
Phase 4
Self-Healing Validation
validation
↓
repair
↓
regenerate
19. Success Metrics

Validation Platform should achieve:

Schema Success Rate
>99%
False Hallucination Detection
<5%
Validation Latency
<100ms

excluding semantic similarity.

Runtime Compatibility
100%

across all runtimes.

20. Implementation Roadmap
Phase 1

Core Foundation

models
interfaces
registry
service
Phase 2

Input Validators

empty prompt
token budget
provider limits
context validation
Phase 3

Output Validators

schema
citations
completeness
consistency
Phase 4

Hallucination Validators

groundedness
unsupported claims
contradictions
Phase 5

Runtime Validators

research
planner
reviewer
agent
mcp
Phase 6

Scoring + Reports

validation reports
policies
regeneration support
Final Architecture
Guardrails
        ↓
Input Validation
        ↓
Generation
        ↓
Structured Outputs
        ↓
Output Validation
        ↓
Hallucination Validation
        ↓
Runtime Validation
        ↓
Validation Report
        ↓
Artifacts
        ↓
Evaluation
