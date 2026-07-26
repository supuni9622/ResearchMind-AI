# Hallucination Testing

**Status:** Partially implemented — production runtime detection exists; dedicated offline test suite does not.

---

## What's implemented

| Component | File | What it does |
|---|---|---|
| `HallucinationValidator` | `app/ai/runtime/generation/validation/output/hallucination_validator.py` | Deterministic, no-LLM groundedness proxy: fraction of the response's significant words (≥4 chars) that also appear in the retrieved context |
| `FaithfulnessGuardrail` | `app/ai/guardrails/generation/faithfulness.py` | Wraps `HallucinationValidator`, reinterprets the same score as a hard `ERROR` (vs. the validator's `WARNING`) |
| `RegenerationPolicy.regenerate_on_hallucination` | `app/ai/guardrails/policies/regeneration_policy.py` | When `True` (default), a `FAITHFULNESS`-category `ERROR` issue triggers `GuardrailAction.REGENERATE` |
| `groundedness()` / `faithfulness()` | `benchmarks/generation/metrics.py` | Offline benchmark scorers — bag-of-words groundedness and sentence-level claim support — used by the engineering benchmark suite, not live traffic |

## How it works

1. `HallucinationValidator` runs only when there's retrieved context to ground against and the response has ≥5 significant words.
2. Groundedness score = `|response_words ∩ context_words| / |response_words|`.
3. Score `< 0.3` → `ValidationIssue` (severity `WARNING`) — advisory only at the Validation layer.
4. `FaithfulnessGuardrail` re-scores the same result at `FAITHFULNESS_THRESHOLD`; below it, raises a `GuardrailIssue` at `ERROR` severity.
5. `GuardrailService`'s regeneration policy turns that `ERROR` into `GuardrailAction.REGENERATE`, re-running generation.
6. Flags are counted via `researchmind_generation_hallucination_flags_total` (Prometheus).

## Not implemented

- `tests/evaluation/test_faithfulness.py`, `tests/evaluation/test_groundedness.py` — empty stub files, no golden dataset
- `tests/security/test_jailbreaks.py`, `test_prompt_injection.py` — empty stubs
- No LLM-judge or semantic-similarity hallucination scoring (lexical overlap only, by design — see file docstrings)
- No CI gate on hallucination rate
