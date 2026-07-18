# Generation

## Dataset

- **Name:** research-papers
- **Documents:** 13
- **Generated:** `2026-07-18T12:18:56.901811+00:00`

## Provenance

- **Git commit:** `9965bd7485da7f5be2aa9e75eb8ef9076448513f`
- **Branch:** `main`
- **Dataset version:** `1.0`
- **Benchmark version:** `1.0.0`
- **Model versions:**
  - `claude`: `claude-sonnet-5`
  - `groq`: `llama-3.3-70b-versatile`
  - `openai`: `gpt-5.5`

---

## Comparison

| Metric | groq | openai | claude | gemini | ollama |
|---|---:|---:|---:|---:|---:|
| Avg Cost Usd | 0.000158 | 0.000249 | 0.003761 | 0.0 | 0.0 |
| Avg Latency Ms | 362.25 | 2417.46 | 3472.79 | 0.0 | 0.0 |
| Citation Accuracy | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| Completeness | 0.7065 | 0.7818 | 0.8727 | 0.0 | 0.0 |
| Cost Per 1K Queries | 0.158 | 0.249 | 3.761 | 0.0 | 0.0 |
| Cost Per Query | 0.000158 | 0.000249 | 0.003761 | 0.0 | 0.0 |
| Faithfulness | 0.8544 | 0.9615 | 0.8869 | 0.0 | 0.0 |
| Groundedness | 0.6276 | 0.7003 | 0.594 | 0.0 | 0.0 |
| Hallucination Rate | 0.1456 | 0.0385 | 0.1131 | 1.0 | 1.0 |
| P95 Latency Ms | 555.69 | 3363.73 | 5680.05 | 0.0 | 0.0 |
| Queries Evaluated | 13 | 13 | 13 | 0 | 0 |
| Relevance | 0.7121 | 0.6884 | 0.7367 | 0.0 | 0.0 |

---

## groq

Version: `llama-3.3-70b-versatile`

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8544 |
| Groundedness | 0.6276 |
| Relevance | 0.7121 |
| Completeness | 0.7065 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1456 |
| Avg Latency Ms | 362.25 |
| P95 Latency Ms | 555.69 |
| Avg Cost Usd | 0.000158 |
| Cost Per Query | 0.000158 |
| Cost Per 1K Queries | 0.158 |

### Notes

- **queries_total**: 13

## openai

Version: `gpt-5.5`

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.9615 |
| Groundedness | 0.7003 |
| Relevance | 0.6884 |
| Completeness | 0.7818 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.0385 |
| Avg Latency Ms | 2417.46 |
| P95 Latency Ms | 3363.73 |
| Avg Cost Usd | 0.000249 |
| Cost Per Query | 0.000249 |
| Cost Per 1K Queries | 0.249 |

### Notes

- **queries_total**: 13

## claude

Version: `claude-sonnet-5`

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8869 |
| Groundedness | 0.594 |
| Relevance | 0.7367 |
| Completeness | 0.8727 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1131 |
| Avg Latency Ms | 3472.79 |
| P95 Latency Ms | 5680.05 |
| Avg Cost Usd | 0.003761 |
| Cost Per Query | 0.003761 |
| Cost Per 1K Queries | 3.761 |

### Notes

- **queries_total**: 13

## gemini

| Metric | Value |
|---|---:|
| Queries Evaluated | 0 |
| Faithfulness | 0.0 |
| Groundedness | 0.0 |
| Relevance | 0.0 |
| Completeness | 0.0 |
| Citation Accuracy | 0.0 |
| Hallucination Rate | 1.0 |
| Avg Latency Ms | 0.0 |
| P95 Latency Ms | 0.0 |
| Avg Cost Usd | 0.0 |
| Cost Per Query | 0.0 |
| Cost Per 1K Queries | 0.0 |

### Notes

- **queries_total**: 13
- **error**: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\nPlease retry in 6.043636803s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerMinute-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerDay-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '6s'}]}}

## ollama

| Metric | Value |
|---|---:|
| Queries Evaluated | 0 |
| Faithfulness | 0.0 |
| Groundedness | 0.0 |
| Relevance | 0.0 |
| Completeness | 0.0 |
| Citation Accuracy | 0.0 |
| Hallucination Rate | 1.0 |
| Avg Latency Ms | 0.0 |
| P95 Latency Ms | 0.0 |
| Avg Cost Usd | 0.0 |
| Cost Per Query | 0.0 |
| Cost Per 1K Queries | 0.0 |

### Notes

- **queries_total**: 13
- **error**: Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible. https://ollama.com/download
