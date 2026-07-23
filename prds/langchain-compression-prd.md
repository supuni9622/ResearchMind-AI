# LangChain Compression Platform PRD

**Project:** ResearchMind AI
**Module:** Knowledge Platform → Context Platform
**Document:** `langchain-compression-prd.md`
**Version:** 1.0
**Status:** Ready for Implementation

---

# 1. Overview

## Objective

Implement a LangChain-powered Context Compression Platform inside ResearchMind to reduce irrelevant retrieved context before generation.

The platform should:

- Reduce token consumption
- Improve answer precision
- Preserve metadata and citations
- Support future adaptive compression strategies
- Integrate seamlessly with Retrieval → Generation pipelines

---

# 2. Problem Statement

Current pipeline:

```text
Query
 ↓
Query Processing
 ↓
Hybrid Retrieval
 ↓
Reranking
 ↓
Generation
```

Problems:

- Too many irrelevant chunks reach generation.
- Token costs become high.
- Long contexts increase hallucination risk.
- Research workflows can exceed model context limits.

---

# 3. Target Architecture

```text
Query
 ↓
Query Processing
 ↓
Hybrid Retrieval
 ↓
Reranking
 ↓
Context Compression
 ↓
Generation
```

---

# 4. Goals

## Functional Goals

1. Remove irrelevant content.
2. Reduce prompt size.
3. Preserve important information.
4. Preserve citations.
5. Support multiple compression providers.
6. Support future adaptive compression.

---

## Non-Functional Goals

- Async-first
- Production ready
- Observable
- Configurable
- Extensible
- Fault tolerant

---

# 5. Architecture Placement

```text
Knowledge Platform
│
├── Query Processing
├── Retrieval
├── Reranking
├── Context Compression   ← NEW
├── Context Assembly
└── Citation Platform
```

---

# 6. Folder Structure

```text
app/
└── ai/
    └── knowledge/
        └── context/
            └── compression/
                ├── __init__.py
                ├── enums.py
                ├── models.py
                ├── exceptions.py
                ├── base.py
                ├── service.py
                │
                ├── providers/
                │   ├── __init__.py
                │   ├── base.py
                │   ├── langchain.py
                │   └── llm.py
                │
                ├── strategies/
                │   ├── extractive.py
                │   ├── summarization.py
                │   ├── adaptive.py
                │   └── metadata.py
                │
                ├── metrics/
                │   ├── token_metrics.py
                │   └── compression_metrics.py
                │
                └── tests/
```

---

# 7. Main Responsibilities

The compression platform must:

1. Receive reranked documents.
2. Compress context.
3. Preserve metadata.
4. Preserve citations.
5. Produce metrics.
6. Emit events.
7. Never break generation.

---

# 8. High-Level Flow

```text
Top-K Documents
        ↓
Compression Service
        ↓
Compression Provider
        ↓
Compression Strategy
        ↓
Compressed Documents
        ↓
Generation
```

---

# 9. Service Interface

## CompressionService

```python
async def compress(
    query: str,
    documents: list[Document],
    config: CompressionConfig,
) -> CompressionResult:
    pass
```

Responsibilities:

- Provider selection
- Metrics
- Tracing
- Error handling
- Fallback handling

---

# 10. Enums

## CompressionProvider

```python
class CompressionProvider(str, Enum):
    LANGCHAIN = "langchain"
    LLM = "llm"
```

---

## CompressionStrategy

```python
class CompressionStrategy(str, Enum):
    EXTRACTIVE = "extractive"
    SUMMARIZATION = "summarization"
    ADAPTIVE = "adaptive"
```

---

# 11. Models

## CompressionConfig

```python
class CompressionConfig(BaseModel):

    enabled: bool = True

    provider: CompressionProvider
    strategy: CompressionStrategy

    compression_ratio: float = 0.5

    max_tokens: int | None = None

    preserve_metadata: bool = True
    preserve_citations: bool = True

    return_intermediate_steps: bool = False
```

---

## CompressionResult

```python
class CompressionResult(BaseModel):

    documents: list[Document]

    original_tokens: int
    compressed_tokens: int

    compression_ratio: float

    provider: str
    strategy: str

    duration_ms: float
```

---

# 12. Provider Architecture

```text
CompressionService
         ↓
BaseCompressionProvider
         ↓
─────────────────────────────
│ LangChain Provider        │
│ Future LLM Provider       │
─────────────────────────────
```

---

# 13. Provider Interface

```python
class BaseCompressionProvider(ABC):

    @abstractmethod
    async def compress(
        self,
        query: str,
        documents: list[Document],
        config: CompressionConfig,
    ) -> CompressionResult:
        pass
```

---

# 14. LangChain Provider

File:

```text
knowledge/context/compression/providers/langchain.py
```

Purpose:

Provide compression capabilities using LangChain retrievers and document compressors.

---

# 15. Supported LangChain Components

## Phase 1

### 1. LLMChainExtractor

Purpose:

Remove irrelevant sections from documents.

Flow:

```text
Document
      ↓
LLMChainExtractor
      ↓
Compressed Document
```

---

### 2. ContextualCompressionRetriever

Purpose:

Query-aware context reduction.

Flow:

```text
Retriever
      ↓
ContextualCompressionRetriever
      ↓
Compressed Documents
```

---

# 16. Future LangChain Components

Future support:

- EmbeddingsFilter
- LLMChainFilter
- CrossEncoderReranker
- CohereRerank
- VoyageAIRerank
- RankLLM
- Semantic Compression

---

# 17. LangChain Provider Responsibilities

### Create Compressor

```python
_create_compressor()
```

---

### Create Contextual Retriever

```python
_create_contextual_retriever()
```

---

### Execute Compression

```python
compress()
```

---

### Restore Metadata

Compression must preserve:

```text
document_id
source_id
chunk_id
parent_chunk_id
page
citations
retrieval_score
rerank_score
session_id
document_type
```

---

# 18. Compression Flow

```text
Reranked Documents
          ↓
Count Tokens
          ↓
LangChain Compression
          ↓
Restore Metadata
          ↓
Compute Metrics
          ↓
Return Result
```

---

# 19. Configuration

Example:

```yaml
knowledge:
  context:
    compression:
      enabled: true

      provider: langchain

      strategy: extractive

      compression_ratio: 0.5

      max_tokens: 12000
```

---

# 20. Metrics

Track:

```text
compression_duration_ms
documents_before
documents_after
original_tokens
compressed_tokens
tokens_saved
compression_ratio
provider
strategy
```

---

# 21. Observability

## Events

```text
context.compression.started
context.compression.completed
context.compression.failed
```

---

## Trace Tags

```text
provider
strategy
documents_before
documents_after
tokens_saved
```

---

# 22. Error Handling

Create:

```python
CompressionException
CompressionProviderException
CompressionTimeoutException
```

---

## Fallback Strategy

Compression must never fail generation.

```text
Compression Failure
        ↓
Return Original Documents
```

---

# 23. Integration Points

## Retrieval Pipeline

```text
retrieve()
     ↓
rerank()
     ↓
compress()
     ↓
generate()
```

---

## Research Runtime

Used for:

- Deep research
- Report generation
- Multi-step synthesis

---

## Agent Runtime

Used for:

- Planner agents
- Reviewer agents
- Tool agents
- Reflection workflows

---

# 24. Future LLM Provider

File:

```text
providers/llm.py
```

---

## Query-Aware Compression

Example:

```text
Extract only information relevant to:

"How did OpenAI's revenue change in 2025?"
```

---

## Adaptive Compression

Compression ratio determined by:

- Model context window
- Remaining token budget
- Runtime type
- Query complexity

---

## Semantic Merging

Merge related chunks before generation.

---

# 25. Acceptance Criteria

## Functional

- [ ] Compression provider abstraction
- [ ] LangChain provider implementation
- [ ] LLMChainExtractor support
- [ ] ContextualCompressionRetriever support
- [ ] Metadata preservation
- [ ] Citation preservation
- [ ] Async support
- [ ] Configuration support
- [ ] Metrics support
- [ ] Event emission
- [ ] Fallback support

---

# 26. Testing Requirements

## Unit Tests

### Service

- Provider selection
- Fallback behavior
- Metrics generation

### Provider

- Compressor creation
- Metadata restoration
- Exception handling

### Metrics

- Token calculations
- Compression ratio calculations

---

## Integration Tests

```text
Retrieve
    ↓
Rerank
    ↓
Compress
    ↓
Generate
```

Validate:

- Metadata integrity
- Citation preservation
- Context quality

---

# 27. Evaluation Metrics

Measure:

```text
Precision before compression
Precision after compression
Latency increase
Token reduction
Answer quality delta
```

Target:

| Metric | Target |
|--------|---------|
| Token Reduction | 30%–70% |
| Quality Drop | <5% |
| Latency Increase | <500 ms |

---

# 28. Implementation Order

## Step 1

Create:

```text
enums.py
models.py
exceptions.py
base.py
```

---

## Step 2

Implement:

```text
providers/base.py
providers/langchain.py
```

---

## Step 3

Implement:

```text
service.py
```

---

## Step 4

Add:

- metrics
- observability
- tests

---

# 29. Definition of Done

The Context Compression Platform is complete when:

1. Retrieval → Compression → Generation pipeline works.
2. Compression is configurable.
3. Metadata survives compression.
4. Metrics are observable.
5. Compression failures safely fallback.
6. Research Runtime uses compressed context.
7. Agent Runtime uses compressed context.
8. Production benchmarks pass.
9. Platform is ready for future adaptive compression.
