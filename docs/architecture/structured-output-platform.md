# Structured Output Platform

---

# Status

🟡 In Progress

Current Completion: ~99%

---

# Purpose

The Structured Output Platform provides deterministic output generation and parsing capabilities for ResearchMind.

Its primary responsibilities are:

- Native provider structured output support
- Output parsing
- Output repair
- Schema validation
- Pydantic integration
- Future tool calling support
- Future agent output contracts

The platform exists to transform unreliable free-form LLM responses into strongly typed application objects.

---

# Architectural Principles

ResearchMind owns:

- Output contracts
- Schemas
- Validation contracts
- Parser orchestration
- Repair logic
- Structured output lifecycle

LangChain is leveraged for:

- JsonOutputParser
- PydanticOutputParser
- `with_structured_output()` (`generation/langchain/output_parsers.py`) —
  OpenAI, Claude, Gemini, Ollama. Not Groq: `langchain-groq` has no
  release compatible with `groq>=1.5.0` (the native `GroqProvider`'s SDK
  floor); adding it would force a downgrade that risks the native
  integration.

---

# Goals

The platform should support:

✅ Research reports

✅ Planner outputs

✅ Reviewer outputs

✅ Agent plans

✅ MCP tool responses

✅ APIs

✅ Future multi-agent workflows

without major architectural changes.

---

# Folder Structure

```text
generation/structured_output/

├── interfaces.py
├── models.py
├── exceptions.py
├── registry.py
├── repair.py
├── service.py
├── create.py
│
├── parsers/
│   ├── json.py
│   ├── pydantic.py
│   ├── markdown.py
│   └── xml.py
│
└── schemas/
    ├── research_report.py
    ├── citations.py
    ├── planner.py
    └── agent.py
```

---

# Platform Responsibilities

The Structured Output Platform owns:

### Parsing

```text
Text → Objects
```

---

### Repair

```text
Broken JSON → Valid JSON
```

---

### Validation

```text
Objects → Schema Validation
```

---

### Provider Integration

```text
Provider Native Structured Output
```

---

### Future Tool Calling

```text
LLM Tool Calls → Objects
```

---

# Core Flow

Current — two branches, selected by `response_format`:

**JSON / STRUCTURED** (provider-native schema support exists):

```text
GenerationRequest
        ↓
response_schema (output_schema / output_model)
        ↓
Provider (generate_structured)
        ↓
Native Structured Output
        ↓
Parser Fallback (json.loads → StructuredOutputRepair)
        ↓
GenerationResult.parsed_output
        ↓
output_model.model_validate() (if output_model is set)
```

**MARKDOWN / XML** (no provider supports schema-constrained Markdown/XML
decoding, so there's nothing for a provider to do natively):

```text
GenerationRequest
        ↓
Provider (generate — plain text)
        ↓
GenerationService._parse_via_registry
        ↓
Structured Output Registry (MarkdownParser / XMLParser)
        ↓
GenerationResult.parsed_output
```

`GenerationService` is constructed with a `StructuredOutputRegistry`
(wired in `generation/create.py` via `structured_output/create.py`'s
`get_structured_output_registry()`), so both branches are reachable
from the same `GenerationService.generate()` entrypoint — the registry
is no longer a disconnected, generation-unaware pipeline. `JsonParser`
and `PydanticParser` remain unused in the generation runtime path
(native decoding + the lean repair fallback already cover JSON/Pydantic
well); the registry is still available standalone for callers that
already have raw text in hand (e.g. non-generation call sites, tests).

Future:

```text
GenerationRequest
        ↓
response_schema
        ↓
Provider
        ↓
Native Structured Output
        ↓
Parser Fallback
        ↓
Validation
```

---

# Core Models

---

## OutputFormat

```text
JSON
PYDANTIC
MARKDOWN
XML
```

---

## StructuredOutputRequest

Contains:

- content
- output_format
- schema
- repair_json

---

## StructuredOutputResult

Contains:

- raw_content
- parsed_content
- success
- errors

---

# Registry

The registry acts as the canonical parser registry.

Responsibilities:

- parser registration
- parser lookup
- future custom parser support

---

# Repair Layer

The repair layer fixes common LLM formatting issues.

Supported repairs:

✅ remove markdown blocks

✅ extract embedded json

✅ trailing commas

✅ single quotes

✅ missing braces

Future repairs:

⬜ unquoted keys

⬜ python booleans

⬜ python None

⬜ nested json strings

---

# Parser Types

---

## JSON Parser

Uses:

```text
LangChain JsonOutputParser
```

---

## Pydantic Parser

Uses:

```text
LangChain PydanticOutputParser
```

This parser is the primary parser for:

- planners
- agents
- reports
- APIs

---

## Markdown Parser

ResearchMind-owned parser.

Primarily for:

- reports
- summaries
- reviewer outputs

---

## XML Parser

Mainly useful for:

- Anthropic XML prompting
- future integrations

---

# Schemas

Current schemas:

---

## ResearchReport

Represents:

- executive summary
- findings
- limitations
- references

---

## PlannerOutput

Represents:

- objective
- plan steps

---

## CitationCollection

Represents:

- extracted citations

---

## AgentExecutionResult

Represents:

- plans
- tool calls
- reviews
- final responses

---

# Native Provider Structured Outputs

---

## OpenAI

Supports:

```python
response_format=
```

Future:

```python
client.beta.chat.completions.parse()
```

---

## Gemini

Supports:

```python
response_mime_type=
response_json_schema=
```

`response_json_schema` (not `response_schema`, which expects Gemini's
restricted OpenAPI-subset `Schema` type) accepts standard JSON Schema —
the shape `output_schema` is already in.

---

## Claude

Supports:

```python
output_config={
    "format": {
        "type": "json_schema",
        "schema": ...,
    }
}
```

Schema-constrained decoding via the native Structured Outputs API. Falls
back to JSON-enforced prompting when no schema is available (JSON mode
without a schema).

---

## Groq

Supports:

```python
response_format={
    "type": "json_schema",
    "json_schema": {"name": ..., "schema": ..., "strict": True},
}
```

Falls back to `{"type": "json_object"}` when no schema is available.

---

## Ollama

Supports:

```python
format=<json_schema>
```

Some models support constrained decoding against a full JSON Schema
passed to `format`. Falls back to `format="json"` (JSON mode) when no
schema is available.

---

# LangChain Structured Output Integration

`generation/langchain/output_parsers.py` — a standalone, optional
alternative to `GenerationService` for callers who want LangChain's
`with_structured_output()` to handle provider formatting, parsing, and
Pydantic validation in a single call, and don't need routing, retries,
cost tracking, or the uniform `GenerationResult` contract.

```python
from app.ai.runtime.generation.langchain.output_parsers import generate_structured

result: PlannerOutput = await generate_structured(
    provider=GenerationProvider.OPENAI,
    model_name="gpt-5-mini",
    schema=PlannerOutput,
    user_prompt="...",
)
```

`generate_structured_from_request(provider, model_name, request)` is a
convenience wrapper that pulls the schema and prompts from an existing
`GenerationRequest` (reuses `request.output_model`).

Backed by each provider's LangChain chat model integration — a separate
client stack from the native SDKs (`AsyncOpenAI`, `AsyncAnthropic`, etc.)
that `GenerationService`'s providers use:

| Provider | Chat model | Package |
| --- | --- | --- |
| OpenAI | `ChatOpenAI` | `langchain-openai` |
| Claude | `ChatAnthropic` | `langchain-anthropic` |
| Gemini | `ChatGoogleGenerativeAI` | `langchain-google-genai` |
| Ollama | `ChatOllama` | `langchain-ollama` |
| Groq | *(unsupported)* | — |

**Groq is not supported.** No released version of `langchain-groq`
(including pre-releases) is compatible with `groq>=1.5.0`, the SDK
floor the native `GroqProvider` requires — every `langchain-groq`
release pins `groq<1`. Adding it would force downgrading the `groq`
package and risk breaking the native integration, so `_build_chat_model`
raises `NotImplementedError` for `GenerationProvider.GROQ` with an
explanation, instead of silently failing or downgrading a shared
dependency. Use `GenerationService` for Groq structured output instead.

This is intentionally **not** wired into `GenerationService.generate()` —
it duplicates provider formatting that `GenerationService` already
handles natively (see Native Provider Structured Outputs above), and
routing every structured request through it would forgo the retry
handling, cost estimation, usage extraction, and structured logging
already built around the native SDKs. It exists as an opt-in path for
call sites that specifically want LangChain's convenience over a single,
one-off structured call.

---

# Provider Strategy

Preferred order:

```text
Native Structured Output
            ↓
Parser Fallback
            ↓
Repair Layer
```

---

# Future Generation Flow

```text
GenerationRequest
        ↓
response_schema
        ↓
Provider Selection
        ↓
Native Structured Output
        ↓
Fallback Parsing
        ↓
Validation
        ↓
GenerationResult
```

---

# Generation Platform Integration

GenerationRequest supports:

```python
response_format

output_schema

output_model
```

`GenerationService.generate()` routes requests with `output_schema` set,
or `response_format` in `{JSON, STRUCTURED}`, through each provider's
`generate_structured()` instead of `generate()`.

Requests with `response_format` in `{MARKDOWN, XML}` instead run
`generate()` (plain text — no provider has native Markdown/XML schema
decoding) and then parse `result.content` through the Structured Output
Registry's `MarkdownParser` / `XMLParser` — see Core Flow above.
`ResponseFormat.XML` was added specifically to make this reachable;
previously there was no way to request XML output at all.

`output_model` (`type[BaseModel] | None`) is a convenience over
`output_schema`: when set and `output_schema` is not explicitly
provided, the schema is derived via `output_model.model_json_schema()`.
Set `model_config = ConfigDict(extra="forbid")` on the model for strict
schema compliance (`additionalProperties: false`) on providers that
enforce it (OpenAI, Groq).

GenerationResult supports:

```python
parsed_output
```

When `output_model` is set, `GenerationService.generate()` validates
`parsed_output` (the dict produced by native structured output or the
parser-repair fallback) back into an instance of `output_model` via
`model_validate()`. This is best-effort — a model that drifted from the
schema is logged (`generation.structured_output.validation_failed`) and
left as the raw dict rather than failing the generation. General JSON
Schema validation independent of `output_model` remains owned by the
Validation Platform (see Platform Boundaries).

Future:

```python
structured_output_used

native_structured_output_used
```

---

# Prompt Platform Integration

`GenerationService.generate_from_template()` bridges the Prompt Platform
(`generation/prompts/` — template loading, variable rendering, few-shot
examples, all pre-existing and already substantial, not stubs) into the
Generation Platform:

```text
PromptTemplate (rendered via PromptService)
        ↓
list[BaseMessage] (system + few-shot + human)
        ↓
flattened into GenerationRequest.system_prompt / .user_prompt
        ↓
output_model set? → append PydanticOutputParser(pydantic_object=output_model)
                       .get_format_instructions()
        ↓
GenerationService.generate()
```

`GenerationRequest` only carries flat `system_prompt`/`user_prompt`
strings (not a message list), so the rendered `ChatPromptTemplate` is
flattened: `SystemMessage` content becomes `system_prompt`; few-shot
pairs (role-labeled, e.g. `"Assistant: ..."`) and the final human
message become `user_prompt`.

Format instructions (`PydanticOutputParser.get_format_instructions()`,
e.g. *"The output should be formatted as a JSON instance that conforms
to the JSON schema below..."*) are schema-aware — generated from the
actual `output_model`, not the generic "return valid JSON" nudge — and
are appended whenever `output_model` is passed to
`generate_from_template()`. They **reinforce** native provider
structured output (`output_config.format` / `response_format` /
`response_json_schema` — see Native Provider Structured Outputs above),
not replace it — both apply on every call, since the prompt is rendered
before a provider is selected, so there's no way to skip the
prompt-level instruction only for providers with reliable native
enforcement.

`generate_from_template()` requires a `PromptService` to be wired in
(`generation/create.py` → `prompts/create.py`'s `get_prompt_service()`)
— calling it without one raises `GenerationValidationError` immediately
rather than failing confusingly partway through. The plain `generate()`
entrypoint is untouched and doesn't require `PromptService` at all.

---

# Validation Platform Integration

Current flow (`generation/validation/`):

```text
Generation
      ↓
Structured Output (parsed_output / content)
      ↓
ValidationService.validate(request=request, result=result, context=...)
      ↓
GenerationResult.validation: ValidationReport
      (input_validation / output_validation / hallucination_validation)
```

`GenerationService.generate()` runs `ValidationService.validate()` as the
last step of each attempt (after the structured-output and `output_model`
steps), attaching a `ValidationReport` (PRD §7) to `GenerationResult.validation`
— one `ValidationResult` per stage, plus a renormalized `overall_score`
(`validation/scoring.py`, PRD §15 weights). It never raises for a failed
validation — the report is there for the caller to inspect and act on.
`validation` stays `None` when no `ValidationService` is wired (backward
compatible with direct `GenerationService(registry=...)` construction).

Only `output_validation.valid` gates the regeneration loop
(`GenerationService._needs_regeneration` / `_build_correction_message`):
input-stage issues (token budget, missing provider capability, ...)
describe the *request*, and re-calling the provider with the same request
plus a corrective note wouldn't fix them — it could even make a
token-budget overflow worse. Hallucination-stage issues are WARNING-only
heuristics and never flip a stage's `valid` to `False` on their own.

Validators are grouped by stage in a `ValidationRegistry`
(`validation/registry.py`, PRD §13) and run through `ValidationService`'s
per-stage methods (`validate_input` / `validate_output` /
`validate_hallucination`) or all at once via `validate()`. Each validator
returns a `ValidatorOutcome` (issues + an optional `score`) rather than a
bare issue list, so stage-level scores can feed the overall formula.

**Input validators** (`generation/validation/input/`) run against
`GenerationRequest` plus an `InputValidationContext` (context window,
capability flags — plain primitives, not `ProviderCapabilities` directly,
to avoid an import cycle with `generation/models.py`):

- **`EmptyPromptValidator`** — empty/whitespace-only `user_prompt`
  (ERROR; unreachable via `GenerationService`, which already hard-rejects
  this before any validator runs — this exists for other, future callers
  without that same gate) or `system_prompt` (WARNING), plus unrendered
  `{placeholder}` template variables left in either (matches
  `PromptBuilder.extract_variables()`'s syntax).
- **`TokenBudgetValidator`** — estimated prompt tokens vs. the resolved
  provider's context window. Deliberately uses the same cheap
  words-×-1.3 approximation `TokenCounter` falls back to on error,
  rather than `TokenCounter`'s real provider API calls — Validation
  Principle 2 (PRD §4) is to stay deterministic and avoid expensive
  calls. WARNING near the limit, ERROR over it; contributes a
  budget-health score.
- **`ProviderLimitsValidator`** — streaming / structured_output /
  json_mode / tool_calling requested but unsupported by the resolved
  provider. Mirrors (doesn't replace) `GenerationService._check_capability_support`'s
  log-only guard — this makes the same signal available as a
  `ValidationIssue` for reuse outside `GenerationService`.
- **`ContextValidator`** — data-quality checks on `request.prompt_context`:
  empty chunk content, duplicate `chunk_id`s, chunks whose `citation_id`
  has no matching `Citation`. All WARNING — these describe upstream
  retrieval quality, not something that should block generation.

**Output validators** (`generation/validation/output/`):

- **`SchemaValidator`** — validates `parsed_output` against
  `request.output_schema` using `jsonschema`. Independent of the
  `output_model` re-validation in `GenerationService._validate_parsed_output`
  (which validates against one specific Pydantic class) — this checks any
  `output_schema`, including a raw dict with no corresponding Pydantic
  model, and catches drift `output_model` validation wouldn't (e.g. a
  provider that skipped native schema enforcement).
- **`JsonValidator`** — checks whether `content` itself is well-formed
  JSON when JSON was expected, independent of `SchemaValidator` (which
  only checks parsed *shape*, after parsing/repair already happened).
  Valid as-is scores 1.0; repairable via `StructuredOutputRepair` is a
  WARNING at 0.5; unparseable even after repair is an ERROR at 0.0.
- **`CitationValidator`** — scans `content` for bracketed citation
  markers (`[S1]`, `[S1, S2]` — the convention `CitationService.build()`
  and the prompt formatters already use) and flags any that don't match
  a `citation_id` in `request.prompt_context.citations`/`chunks`,
  catching fabricated citations. Skips entirely when the prompt context
  carries no known citations, so it never false-positives on generations
  that weren't grounded in retrieved sources.

**Hallucination validator** (`generation/validation/output/hallucination_validator.py`,
registered under the `hallucination` stage, not `output`):

- **`HallucinationValidator`** — lightweight, deterministic groundedness
  proxy (PRD §10, no LLM judge): the fraction of the response's
  "significant" words (≥4 chars) that also appear in the retrieved
  context. WARNING (never ERROR — biased toward the PRD's <5%
  false-positive target) below a 0.3 threshold; always contributes a
  groundedness score when there's enough context/content to measure.
  Coarser than the PRD's proposed semantic-similarity `source_overlap_validator`
  but keeps this stage cheap and deterministic.

Not yet implemented:

- Runtime Validators (PRD §11 — research/planner/reviewer/agent/mcp) and
  the Contracts layer (PRD §12). `ValidationStage.RUNTIME` and
  `ValidationReport.runtime_validation` exist as placeholders (always
  `None` today).
- The standalone `validation/` top-level folder structure (PRD §6) —
  this still lives inside `generation/validation/`, following the
  Generation Platform's existing module layout.
- `Artifacts` — the step after `Validation` in the original future flow
  is still future.

---

# Regeneration Strategy

```text
Attempt 1
    ↓
parsed_output is None, or ValidationResult.valid is False
    ↓
Regenerate — provider call again, with corrective feedback appended
    ↓
Valid Output (or attempts exhausted — last result returned as-is)
```

Opt-in — `GenerationRequest.max_regeneration_attempts: int = 0`. Default
0 means no behavior change for any existing caller. When set >0,
`GenerationService.generate()` re-calls the provider up to that many
extra times whenever the latest attempt still needs regeneration:

- a structured request (`output_schema`/`output_model`/`response_format`
  in `{JSON, STRUCTURED}`) whose `parsed_output` is `None`, or
- `ValidationResult.valid` is `False` (schema mismatch, fabricated
  citation, …) — ties the loop to the `ValidationService` above.

Each retry appends a corrective instruction to `system_prompt` (built
fresh from the *latest* failure only — corrections don't accumulate
across attempts) rather than silently re-asking the identical prompt:
a structured request with no `parsed_output` gets a "return ONLY valid
JSON" instruction, a validation failure gets the specific issue
messages (e.g. naming the fabricated citation), and both combine when
both apply. `GenerationResult.regeneration_attempts` records how many
extra calls were made (0 = first attempt accepted, or regeneration
wasn't requested) — essential for agents that need to know whether the
result they got was first-try or coerced. Exhausting the budget without
success is not an error: the last attempt's `GenerationResult` is
returned as-is, `validation`/`parsed_output` intact, for the caller to
inspect (matches every other step in this platform — best-effort,
non-raising).

This lives in `GenerationService` (not per-provider) so it reuses the
same structured-parsing and validation pipeline every attempt runs
through — no provider needs its own retry-on-invalid-output logic.

---

# Provider Capability Flags

`ProviderCapabilities` (`generation/models.py`) and the matching
`supports_*` accessors on `GenerationProviderInterface`
(`generation/interfaces.py`) already existed before any of the work in
this doc — `structured_output`, `json_mode`, `tool_calling`, plus
`streaming`, `reasoning`, `vision`, `citations`, `thinking_tokens`,
`parallel_tool_calls`, `multimodal_input`/`output`. `catalog/models.py`
carries them further — a full model catalog (`ALL_MODELS`,
`MODELS_BY_PROVIDER`) with per-model `capabilities` *and* cost data.

What didn't exist: anything that *uses* the flags. `generation/routing/`
(`service.py`, `interfaces.py`, `models.py`, the three `policies/*.py`,
all six `strategies/*.py`) is entirely empty stubs — there is no
capability-based provider selection, and `GenerationService.generate()`
always requires an explicit `provider:` from the caller. Building that
(multiple strategies, a scoring/fallback policy) is a separate, larger
initiative — out of scope here.

What's implemented instead is a lightweight guard:
`GenerationService._check_capability_support()` runs once per
`generate()` call, before the first attempt. If the explicitly-chosen
provider doesn't declare `structured_output` for a structured request,
`json_mode` for a JSON-format request, or `tool_calling` when
`request.tools` is set, it logs `generation.capability_mismatch` with
the missing capability names. It never blocks the call — capability
flags are self-reported and every provider already degrades gracefully
(e.g. Claude falls back to prompt-enforced JSON without a schema) — this
only makes that degradation observable instead of silent.

---

# Runtime Integration

The platform will be heavily used by:

---

## Research Runtime

Research reports.

---

## Planner Runtime

Planner contracts.

---

## Reviewer Runtime

Reviewer outputs.

---

## Agent Runtime

Tool calls and plans.

---

## MCP Runtime

Tool invocation payloads.

---

# Future Extensions

Potential additions:

```text
Tool Call Parser

Streaming Structured Outputs

Schema Versioning

Semantic Schema Validation

Auto Retry On Parse Failure

with_structured_output()

OpenAPI Schema Generation
```

---

# Platform Boundaries

Structured Output Platform DOES NOT own:

❌ Prompt Rendering

❌ Runtime Orchestration

❌ Validation Logic

❌ Tool Execution

❌ Agent State

These belong to:

```text
Prompt Platform

Validation Platform

Research Runtime

Agent Runtime
```

---

# Completion Status

Models                         ✅

Schemas                        ✅

Parsers                        ✅

Repair Layer                   ✅

Registry                       ✅

Factory                        ✅

Service                        ✅

Provider Native Outputs        ✅

Generation Integration         ✅

LangChain with_structured_output ✅ (OpenAI/Claude/Gemini/Ollama; Groq unsupported — see LangChain Structured Output Integration)

Validation Platform Integration ✅ (input/output/hallucination stage validators, registry, scoring, ValidationReport — see Validation Platform Integration)

Regeneration Strategy          ✅ (opt-in via max_regeneration_attempts — see Regeneration Strategy)

Provider Capability Flags      🟡 (flags + accessors pre-existed; capability guard added, but routing/ itself is still empty stubs — see Provider Capability Flags)

Prompt Integration             ✅ (generate_from_template() — see Prompt Platform Integration)

Tests                          ⬜

Current Completion: ~99%
