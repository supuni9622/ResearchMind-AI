# ADR-021
# Hybrid Retrieval Architecture

**Status:** Accepted

---

# Decision

ResearchMind adopts Hybrid Retrieval using:

```text
Dense Retrieval
        +
Sparse Retrieval
        ↓
Reciprocal Rank Fusion
```

Fusion is implemented at the application layer.

---

# Consequences

Benefits:

- observability
- benchmarking flexibility
- easier experimentation
- future weighted fusion

Tradeoffs:

- slightly higher latency
- additional implementation complexity

---

# Canonical Hybrid Workflow

```text
Question
      ↓
Dense Search
      ↓
Sparse Search
      ↓
RRF
      ↓
Top-K
```

---

# Future Extensions

Future improvements:

- weighted RRF
- relative score fusion
- reranking integration
- query decomposition
- context compression
