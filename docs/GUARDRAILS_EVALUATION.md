# Guardrails Evaluation — Custom vs. NeMo Guardrails vs. Llama Guard vs. Lakera Guard

**Purpose:** the "evaluate" half of `PHASE_2_3_ROADMAP.md` V3 #3 — *"benchmark NeMo Guardrails (or LlamaGuard/Lakera) against the existing custom system's actual false-positive/false-negative rate... before committing engineering time to integrating a third-party engine."* This document is the evaluation itself: what our current system actually does (verified against code, not the PRD's aspirational description), and what each third-party provider actually offers (verified against each vendor's own documentation, linked throughout). **Companion docs:** [`PHASE_2_3_ROADMAP.md`](PHASE_2_3_ROADMAP.md) V3 #3, [`EVALUATION_PLAN.md`](EVALUATION_PLAN.md) §9 (the adversarial-dataset mechanism this doc's recommendation depends on), [`AI_ENGINEERING_AUDIT.md`](AI_ENGINEERING_AUDIT.md).

**Headline finding, stated up front:** our current system has **zero measured accuracy** — no benchmark, no labeled corpus, no FP/FN rate computed anywhere (confirmed by code search, §1). Every accuracy number quoted for the three vendors below is *their own marketing/documentation claim*, not independently verified against our traffic. **This document cannot tell you which system is more accurate for ResearchMind — no one can, until the adversarial dataset in `EVALUATION_PLAN.md` §9 exists and all four are run against it.** What it can tell you, precisely: what each system architecturally covers, what ours is currently missing, and how hard each would be to integrate.

---

## 1. What we have today — verified against code, not the PRD

16 named checks across 4 stages (`apps/api/app/ai/guardrails/`). Every technique is **regex, static lookup table, or threshold arithmetic — no ML model, no embeddings, no LLM call, no third-party API anywhere in this package.**

| Stage | Check | Status | Technique |
|---|---|---|---|
| Input | Prompt injection | ✅ Real | 6 hardcoded regexes ("ignore instructions", "reveal system prompt", "act as admin", "DAN", "jailbreak") |
| Input | PII detection | ✅ Real, warn-only | 4 regex patterns: email, credit-card-shaped digits, API-key-shaped strings, generic 32+-char token |
| Input | Scope validation | ✅ Real | 6 regexes across 2 categories (off-topic creative writing, hacking requests) |
| Input | Toxicity | ❌ **Stub** | `return []` unconditionally — docstring: *"seam exists so a future classifier-backed provider (Llama Guard or similar) can be dropped in"* |
| Input | Rate limit | ❌ **Stub** | `return []` unconditionally — *"no request-counting state exists anywhere"* (this specific guardrail; a separate, real Valkey-based limiter exists elsewhere in the app, unrelated to this stub) |
| Retrieval | Source trust | ✅ Real | Static dict lookup of a trust score by source type |
| Retrieval | Context sanitization | ✅ Real | Second regex table (10 patterns) targeting RAG-borne injection in retrieved chunks |
| Retrieval | Citation integrity | ✅ Real | Set-membership check — cited IDs must exist in the retrieved chunk set |
| Retrieval | Access control | ❌ **Stub** | Only a permissive always-allow provider registered — *"No tenant isolation / document ACL / workspace permission model exists in this codebase yet"* |
| Generation | Faithfulness | ✅ Real, not ML | Lexical-overlap heuristic (`HallucinationValidator`), not semantic similarity or an LLM judge |
| Generation | Moderation | ❌ **Stub** | Only an always-allow provider registered |
| Generation | Schema enforcement | ✅ Real | JSON-Schema validation of structured output |
| Generation | PII leakage | ✅ Real, warn-only | Same regex table as input PII, run on model output |
| Runtime | Budget guardrail | ✅ Real logic, **but dead in production** | Threshold checks over tokens/cost/tool-calls/iterations/time — never invoked by any live call site |
| Runtime | Loop detection | ✅ Real logic, **but dead in production** | Set-dedup + threshold — never invoked by any live call site |
| Runtime | Approval gate | ❌ **Interface only, unreachable** | `GuardrailAction.ESCALATE` is dead code end-to-end — no concrete implementation exists anywhere |

**Wiring per surface** (revises an earlier, less precise assumption in this planning cycle): Chat, Linear Research, and Deep Research **all share one `GenerationService`**, so input and generation stages fire identically on all three. Retrieval-stage checks are only meaningfully exercised on Linear/Deep Research, since Chat's context is always empty by design. **The runtime stage (budget/loop enforcement) never fires on any surface** — nothing in production enforces token, cost, or iteration ceilings via this system, including on Deep Research's agentic loop.

**One structural fact that matters for everything below:** `apps/api/app/ai/knowledge/context/guardrails/enums.py` already defines a `GuardrailStrategy` enum with exactly four members — `RULE_BASED`, `LLAMA_GUARD`, `NEMO`, `LAKERA`. Only `RULE_BASED` is implemented; the other three are reserved, unimplemented enum values. This is the one place in the codebase that already names all three vendors in this report as intended future strategies — but it's scaffolding, not integration, and it's scoped narrowly (see §5).

**No benchmark exists.** `benchmarks/` has no guardrails suite. `tests/unit/ai/guardrails/` (33 files) checks specific inputs trigger/don't-trigger specific rules — none run against a labeled corpus or compute precision/recall. A PRD (`prds/guardrails_platform_prd.md`) states target metrics (Prompt Injection Detection >90%, False Positives <5%, latency <50ms) — these are **design goals, never measured**, and should not be cited as our system's actual performance anywhere.

---

## 2. Provider profiles

### 2a. NVIDIA NeMo Guardrails

Open-source (Apache 2.0), Python toolkit, self-hostable as either a library or a containerized microservice (Kubernetes/Helm) — no forced SaaS dependency, no per-request vendor cost.

| Rail type | What it does |
|---|---|
| **Input** | Content safety, jailbreak detection, topic control, PII masking — before the LLM is called |
| **Dialog** | Multi-turn flow control and guided conversations — enforces policy *across* turns, not just per-message |
| **Retrieval** | Document filtering, chunk validation — RAG-specific, filters untrusted context before it reaches the LLM |
| **Execution** | Validates tool/function calls, their arguments, and results — agentic/tool-use specific |
| **Output** | Response filtering, **fact-checking**, sensitive-data removal, hallucination detection |

Guardrail logic is defined via **Colang**, a DSL for conversational flows, plus Python custom actions — genuinely programmable, not a fixed rule set. Integrates with OpenAI, Azure, Anthropic, HuggingFace, and NVIDIA NIM models; supports plugging in classifier backends for specific checks — NVIDIA's own "Llama 3.1 NemoGuard 8B Content Safety" model, community Llama Guard, third-party engines (ActiveFence, Cisco AI Defense, Prompt Security, Pangea AI Guard), and PII engines (GLiNER, Presidio, Private AI, Polygraf).

**Structurally the most different from what we have**: NeMo Guardrails is a full orchestration framework with its own dialog-management layer (Colang), not just a set of per-message checks — adopting it isn't "swap in a detector," it's adopting a second policy/flow engine alongside our existing Generation Runtime.

*Sources: [NVIDIA NeMo Guardrails — Rail Types](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types), [NVIDIA NeMo Guardrails — Overview](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview), [NVIDIA-NeMo/Guardrails on GitHub](https://github.com/NVIDIA-NeMo/Guardrails)*

### 2b. Meta Llama Guard

**Not a framework — a fine-tuned classifier model**, open-weights, self-hosted (run it yourself via HuggingFace/vLLM/NVIDIA NIM, etc.; no hosted API is provided by Meta). This is a materially different kind of thing than NeMo or Lakera: Llama Guard doesn't do rails, dialog management, tool validation, or PII detection — it does exactly one job, safety classification, and does it as an LLM call, not a rule set.

**Llama Guard 3-8B** (fine-tuned from Llama-3.1-8B) classifies both **prompts and responses** against a 14-category hazard taxonomy:

| Code | Category | Code | Category |
|---|---|---|---|
| S1 | Violent Crimes | S8 | Intellectual Property |
| S2 | Non-Violent Crimes | S9 | Indiscriminate Weapons |
| S3 | Sex-Related Crimes | S10 | Hate |
| S4 | Child Sexual Exploitation | S11 | Suicide & Self-Harm |
| S5 | Defamation | S12 | Sexual Content |
| S6 | Specialized Advice | S13 | Elections |
| S7 | Privacy | S14 | Code Interpreter Abuse |

Trained on English data plus synthetic and human-annotated multilingual examples, with tool-use-specific training data and curated benign examples specifically to reduce false positives. Outputs a safe/unsafe decision derived from the model's own token-probability confidence (threshold-tunable), not a hardcoded rule. Meta's own documentation flags a real limitation directly relevant to a research product: *"some hazard categories may require factual, up-to-date knowledge to be evaluated"* (e.g. Defamation, IP, Elections) — the model can misjudge categories that need current facts it wasn't trained with.

**Llama Guard 4** (12B) extends this to multimodal (image+text) input, aligned to the MLCommons standardized hazard taxonomy, as a single classifier meant to safeguard Llama 4's multimodal capabilities specifically.

Notably: **no prompt-injection-specific detection, no PII detection, no jailbreak-pattern detection** — Llama Guard's taxonomy is about *harmful content categories*, not the injection/jailbreak/PII surface our system and NeMo/Lakera both target. It would slot in as one detector for one class of risk (harmful content), not a replacement for the whole system.

*Sources: [Llama Guard 3-8B Model Card](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard3/8B/MODEL_CARD.md), [Llama Guard 4 — Model Cards and Prompt Formats](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/), [Llama Guard 4 12B Model Card](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard4/12B/MODEL_CARD.md)*

### 2c. Lakera Guard

**Commercial, API-based, real-time.** Important, citable procurement fact: **Lakera was acquired by Check Point in September 2025** and is now marketed as part of Check Point's AI Security platform — data-handling documentation now refers to "Check Point systems," which is worth factoring into any vendor decision (data residency, contract terms, and roadmap continuity all sit with a different, larger company than when Lakera was independent).

| Capability | What it does |
|---|---|
| **Prompt injection / jailbreak** | ML-based (not regex), direct and indirect — indirect coverage explicitly scans fetched content, attachments, and URLs (HTML, PDFs) for embedded instructions, which is a category of attack (RAG-borne injection) our own regex-based `context_sanitization` check only partially covers |
| **PII / data leakage** | 8 entity types: full names, US mailing addresses, US phone numbers, emails, IPv4/IPv6, credit cards (Luhn-validated), IBANs, US SSNs — vs. our 4 regex-based types with no NER, no name/address/SSN coverage at all |
| **Content moderation** | Profanity, unsafe-content categories, malicious-link detection — an area our system has as a pure stub |
| **Custom detectors** | Pattern/keyword/document-type rules, including system-prompt-extraction prevention |

Vendor-published performance claims (not independently verified against our traffic): 98%+ prompt-injection detection, sub-50ms latency (one page cites <12ms average), 100+ languages, 0.01% false-positive rate, "100,000+ new attacks analyzed daily" feeding continuous model updates. Deployment: SaaS by default; self-hosted/on-prem available on enterprise plans. Per-project configurable policies determine which detectors run; API responses include per-detector breakdown and match-location payloads.

*Sources: [Lakera — Prompt Injection Attacks](https://www.lakera.ai/risk/prompt-injection-attacks), [Lakera Docs — Data Leakage Prevention](https://docs.lakera.ai/docs/data-leakage-prevention), [Lakera — AI Data Leaks](https://www.lakera.ai/risk/ai-data-leakage)*

---

## 3. Head-to-head comparison

| Capability | ResearchMind (current) | NeMo Guardrails | Llama Guard | Lakera Guard |
|---|---|---|---|---|
| Prompt injection detection | ✅ Regex (6 patterns) | ✅ Heuristic + self-check + NemoGuard classifier | ❌ Not this model's job | ✅ ML, direct + indirect, claims 98%+ |
| Indirect/RAG-borne injection | 🟡 Separate regex table, retrieval stage only | ✅ Retrieval rails, document/chunk filtering | ❌ | ✅ Scans fetched content/attachments/URLs |
| Jailbreak detection | 🟡 Folded into prompt-injection regexes | ✅ Dedicated heuristic + NemoGuard | 🟡 Only if it maps to a hazard category | ✅ Explicit capability |
| PII detection | 🟡 4 regex types, warn-only, no blocking | ✅ Pluggable (GLiNER/Presidio/Private AI/Polygraf) | ❌ | ✅ 8 entity types incl. names/addresses/SSN, block-or-mask |
| Content moderation / toxicity | ❌ Stub | ✅ Content-safety rails + classifier integrations | ✅ **This is its core job** — 14-category hazard taxonomy | ✅ Profanity + unsafe-content categories |
| Fact-checking / hallucination detection | 🟡 Lexical-overlap heuristic only, not semantic | ✅ Dedicated output-rail feature | ❌ | ❌ Not this product's focus |
| Tool/function-call validation | 🟡 Real logic, but policy provider is always-allow | ✅ Dedicated execution rails | ❌ | 🟡 Scans `tool` role messages for PII/injection, not call-correctness |
| Multi-turn dialog policy | ❌ Not a concept in our system | ✅ Dialog rails, Colang flows | ❌ | ❌ |
| Budget/loop/runtime limits | 🟡 Real logic, **dead in production** | 🟡 Not this system's focus (execution rails are about safety, not cost) | ❌ | ❌ |
| Multimodal (image) safety | ❌ | 🟡 Not a stated focus | ✅ Llama Guard 4, 12B, image+text | 🟡 Not confirmed in reviewed docs |
| Approval/escalation (HITL) | ❌ Dead code, unreachable | 🟡 Possible via custom Colang flow, not built-in | ❌ | ❌ |
| Self-hostable, no per-request cost | ✅ | ✅ | ✅ (open weights) | ❌ SaaS by default (on-prem on enterprise plans only) |
| Measured accuracy against our data | ❌ **None exists** | ❌ Would need benchmarking | ❌ Would need benchmarking | ❌ Vendor claims only, unverified on our traffic |

Legend: ✅ full/real coverage · 🟡 partial or structurally present but not effective · ❌ absent

---

## 4. What's actually missing, by provider

| Gap in our current system | Closed by NeMo | Closed by Llama Guard | Closed by Lakera |
|---|---|---|---|
| No ML-based detection anywhere (pure regex, evadable by paraphrase/unicode) | ✅ (classifier integrations) | ✅ (it *is* a classifier) | ✅ (ML-based, vendor's core claim) |
| No content moderation / toxicity | ✅ | ✅ — best fit, this is its exact purpose | ✅ |
| PII coverage limited to 4 regex types, no names/addresses/SSNs | ✅ (pluggable PII engines) | ❌ not in scope | ✅ — richest PII coverage of the three |
| Runtime budget/loop enforcement built but never wired to production | Partially — execution rails validate tool calls, not cost/time budgets | ❌ | ❌ |
| Approval-gate escalation is dead code | 🟡 buildable via Colang, not out-of-the-box | ❌ | ❌ |
| No fact-checking / hallucination detection beyond lexical overlap | ✅ — dedicated output-rail feature | ❌ | ❌ |
| No multi-turn dialog policy (each message evaluated independently) | ✅ — this is a core NeMo differentiator | ❌ | ❌ |
| No multimodal safety coverage | ❌ | ✅ Llama Guard 4 | 🟡 unconfirmed |
| No measured FP/FN rate | ❌ — still needs benchmarking even after adoption | ❌ | ❌ — vendor numbers aren't validated on our data |

**No single provider closes every gap.** NeMo is the broadest structural match (closes 6 of 9 rows) but is architecturally the biggest adoption — it's a second orchestration layer, not a detector to bolt on. Llama Guard closes exactly one gap extremely well (content moderation) and nothing else — it's a component, not a system. Lakera closes the PII and injection gaps most thoroughly per its own claims, at the cost of being the only non-self-hostable-by-default option and now sitting inside a larger acquiring company's platform.

---

## 5. Integration fit — what the codebase already anticipates

The existing `GuardrailProvider` seam (`apps/api/app/ai/knowledge/context/guardrails/`) is a real, working strategy-keyed abstraction — `GuardrailProvider.validate(chunks) -> GuardrailResult`, registered by `GuardrailStrategy` enum value, looked up at call time. This is exactly the shape needed to plug in **Llama Guard or Lakera as a single detector for one check** (it already reserves `LLAMA_GUARD` and `LAKERA` as enum values for precisely this).

**It is not the right shape for NeMo Guardrails.** NeMo isn't a single detector — it's a rails/dialog orchestration framework with its own flow engine. Adopting it as "one more `GuardrailStrategy`" would misrepresent what it actually is; a real NeMo integration would sit alongside (or partially replace) the Generation Runtime's own request-handling flow, not slot into this one seam. This is worth deciding explicitly rather than defaulting into treating all three vendors as interchangeable "strategy" options just because the enum lists them side by side.

The other 15 checks (everything outside `context/guardrails`) have **no shared provider abstraction at all** — each is a hardcoded class. Integrating any vendor for, say, PII or content moderation would mean writing a new class per check and rewiring `create.py`, not swapping a single backend.

---

## 6. Recommendation

Consistent with `PHASE_2_3_ROADMAP.md` V3 #3's original framing — **this is still an evaluate-then-decide item, not a decision this document makes.** What this evaluation adds: a precise map of *what* to test and *why*, instead of an assumed default.

1. **Build the adversarial dataset first** (`EVALUATION_PLAN.md` §9, already planned, 10-20 hand-built cases: prompt injection in an uploaded document, poisoned instructions, known jailbreak patterns). Without this, "NeMo/Llama Guard/Lakera is better" is just repeating vendor marketing copy.
2. **Run our current 16-check system against it first** — establishes the real (not PRD-assumed) baseline FP/FN rate, closing the gap identified in §1.
3. **Given the different natures of the three vendors, they don't compete for the same decision:**
   - **Llama Guard**: cheapest to trial (open weights, one model, one job) — worth testing as a drop-in replacement specifically for the content-moderation stub, independent of any NeMo/Lakera decision.
   - **Lakera**: worth trialing specifically for PII detection (richest entity coverage of the three) and indirect-injection detection (its stated specialty), with the Check Point acquisition weighed as a real vendor-risk factor, not just a technical one.
   - **NeMo Guardrails**: the only one of the three that would be a genuine architecture decision, not a detector swap — evaluate its dialog/fact-checking/execution-rail capabilities specifically against gaps nothing else here closes (multi-turn policy, hallucination detection, budget/loop enforcement that's currently dead code), and treat "adopt NeMo" as a materially bigger decision than "add a Lakera or Llama Guard detector."
4. **Don't adopt any of the three to fix stubs that are stubs by inaction, not by difficulty** — `access_control` (no tenant/ACL model exists yet) and `approval_gate` (needs LangGraph interrupt wiring, which now exists per this planning cycle's Deep Research work) are gaps in *our own* design, not gaps a third-party detector closes.

---

## Sources

- [NVIDIA NeMo Guardrails — Guardrail Types](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/rail-types)
- [NVIDIA NeMo Guardrails — Overview](https://docs.nvidia.com/nemo/guardrails/about-nemo-guardrails-library/overview)
- [NVIDIA-NeMo/Guardrails (GitHub)](https://github.com/NVIDIA-NeMo/Guardrails)
- [Llama Guard 3-8B Model Card (Meta, PurpleLlama)](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard3/8B/MODEL_CARD.md)
- [Llama Guard 4 — Model Cards and Prompt Formats (Meta)](https://www.llama.com/docs/model-cards-and-prompt-formats/llama-guard-4/)
- [Llama Guard 4 12B Model Card (Meta, PurpleLlama)](https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Guard4/12B/MODEL_CARD.md)
- [Lakera — Prompt Injection Attacks](https://www.lakera.ai/risk/prompt-injection-attacks)
- [Lakera Docs — Data Leakage Prevention](https://docs.lakera.ai/docs/data-leakage-prevention)
- [Lakera — AI Data Leaks / Sensitive Information Exposure](https://www.lakera.ai/risk/ai-data-leakage)
