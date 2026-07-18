# Generation

## Dataset

- **Name:** research-papers
- **Documents:** 13
- **Generated:** `2026-07-18T11:05:03.759675+00:00`

---

## Comparison

| Metric | groq | openai | claude | gemini | ollama |
|---|---:|---:|---:|---:|---:|
| Avg Latency Ms | 1334.04 | 2974.43 | 3816.78 | 0.0 | 0.0 |
| Citation Accuracy | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| Completeness | 0.7191 | 0.7736 | 0.8492 | 0.0 | 0.0 |
| Faithfulness | 0.8544 | 0.9615 | 0.8413 | 0.0 | 0.0 |
| Groundedness | 0.6295 | 0.6897 | 0.6321 | 0.0 | 0.0 |
| Hallucination Rate | 0.1456 | 0.0385 | 0.1587 | 1.0 | 1.0 |
| P95 Latency Ms | 4316.84 | 8977.48 | 7315.56 | 0.0 | 0.0 |
| Queries Evaluated | 13 | 13 | 13 | 0 | 0 |
| Relevance | 0.7175 | 0.64 | 0.6974 | 0.0 | 0.0 |

---

## groq

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8544 |
| Groundedness | 0.6295 |
| Relevance | 0.7175 |
| Completeness | 0.7191 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1456 |
| Avg Latency Ms | 1334.04 |
| P95 Latency Ms | 4316.84 |

### Notes

- **queries_total**: 13

## openai

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.9615 |
| Groundedness | 0.6897 |
| Relevance | 0.64 |
| Completeness | 0.7736 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.0385 |
| Avg Latency Ms | 2974.43 |
| P95 Latency Ms | 8977.48 |

### Notes

- **queries_total**: 13

## claude

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8413 |
| Groundedness | 0.6321 |
| Relevance | 0.6974 |
| Completeness | 0.8492 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1587 |
| Avg Latency Ms | 3816.78 |
| P95 Latency Ms | 7315.56 |

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

### Notes

- **queries_total**: 13
- **error**: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\nPlease retry in 59.204928191s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'model': 'gemini-2.5-pro', 'location': 'global'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', 'quotaDimensions': {'model': 'gemini-2.5-pro', 'location': 'global'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerMinute-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerDay-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '59s'}]}}

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

### Notes

- **queries_total**: 13
- **error**: Failed to connect to Ollama. Please check that Ollama is downloaded, running and accessible. https://ollama.com/download
