# Structured Output Platform

---

# Status

🟡 In Progress

Current Completion: ~95%

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
- Future with_structured_output()

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

Current:

```text
GenerationRequest
        ↓
response_schema
        ↓
Provider (generate_structured)
        ↓
Native Structured Output
        ↓
Parser Fallback (json.loads → StructuredOutputRepair)
        ↓
GenerationResult.parsed_output
```

The `Structured Output Service` (registry + parsers/json.py,
parsers/pydantic.py, etc.) remains available as a standalone
text → objects pipeline for callers that already have raw text
in hand (e.g. non-generation call sites, tests) and is used inside
the Prompt/Validation platforms' future flows below.

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
```

`GenerationService.generate()` routes requests with `output_schema` set,
or `response_format` in `{JSON, STRUCTURED}`, through each provider's
`generate_structured()` instead of `generate()`.

GenerationResult supports:

```python
parsed_output
```

Future:

```python
structured_output_used

native_structured_output_used
```

---

# Prompt Platform Integration

Future prompts may inject:

```text
format instructions
```

Examples:

```python
PydanticOutputParser.get_format_instructions()
```

This allows prompts to guide providers toward valid outputs.

---

# Validation Platform Integration

Future flow:

```text
Generation
      ↓
Structured Output
      ↓
Validation
      ↓
Artifacts
```

Validation responsibilities:

- schema validation
- citation validation
- groundedness validation
- completeness validation

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

Prompt Integration             ⬜

Tests                          ⬜

Current Completion: ~95%
