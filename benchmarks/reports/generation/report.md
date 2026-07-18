# Generation

## Dataset

- **Name:** research-papers
- **Documents:** 13
- **Generated:** `2026-07-18T11:54:16.525986+00:00`

---

## Comparison

| Metric | groq | openai | claude | gemini | ollama |
|---|---:|---:|---:|---:|---:|
| Avg Cost Usd | 0.000159 | 0.000247 | 0.003759 | 0.0 | 0.0 |
| Avg Latency Ms | 2400.32 | 2689.41 | 3905.7 | 0.0 | 0.0 |
| Citation Accuracy | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 |
| Completeness | 0.7159 | 0.7914 | 0.8469 | 0.0 | 0.0 |
| Cost Per 1K Queries | 0.159 | 0.247 | 3.759 | 0.0 | 0.0 |
| Cost Per Query | 0.000159 | 0.000247 | 0.003759 | 0.0 | 0.0 |
| Faithfulness | 0.8416 | 0.9615 | 0.8487 | 0.0 | 0.0 |
| Groundedness | 0.6301 | 0.6957 | 0.5873 | 0.0 | 0.0 |
| Hallucination Rate | 0.1584 | 0.0385 | 0.1513 | 1.0 | 1.0 |
| P95 Latency Ms | 21311.73 | 5032.63 | 6645.18 | 0.0 | 0.0 |
| Queries Evaluated | 13 | 13 | 13 | 0 | 0 |
| Relevance | 0.7121 | 0.6801 | 0.7155 | 0.0 | 0.0 |

---

## groq

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8416 |
| Groundedness | 0.6301 |
| Relevance | 0.7121 |
| Completeness | 0.7159 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1584 |
| Avg Latency Ms | 2400.32 |
| P95 Latency Ms | 21311.73 |
| Avg Cost Usd | 0.000159 |
| Cost Per Query | 0.000159 |
| Cost Per 1K Queries | 0.159 |

### Notes

- **queries_total**: 13

## openai

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.9615 |
| Groundedness | 0.6957 |
| Relevance | 0.6801 |
| Completeness | 0.7914 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.0385 |
| Avg Latency Ms | 2689.41 |
| P95 Latency Ms | 5032.63 |
| Avg Cost Usd | 0.000247 |
| Cost Per Query | 0.000247 |
| Cost Per 1K Queries | 0.247 |

### Notes

- **queries_total**: 13

## claude

| Metric | Value |
|---|---:|
| Queries Evaluated | 13 |
| Faithfulness | 0.8487 |
| Groundedness | 0.5873 |
| Relevance | 0.7155 |
| Completeness | 0.8469 |
| Citation Accuracy | 1.0 |
| Hallucination Rate | 0.1513 |
| Avg Latency Ms | 3905.7 |
| P95 Latency Ms | 6645.18 |
| Avg Cost Usd | 0.003759 |
| Cost Per Query | 0.003759 |
| Cost Per 1K Queries | 3.759 |

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
- **error**: 429 RESOURCE_EXHAUSTED. {'error': {'code': 429, 'message': 'You exceeded your current quota, please check your plan and billing details. For more information on this error, head to: https://ai.google.dev/gemini-api/docs/rate-limits. To monitor your current usage, head to: https://ai.dev/rate-limit. \n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_requests, limit: 0, model: gemini-2.5-pro\n* Quota exceeded for metric: generativelanguage.googleapis.com/generate_content_free_tier_input_token_count, limit: 0, model: gemini-2.5-pro\nPlease retry in 46.350913365s.', 'status': 'RESOURCE_EXHAUSTED', 'details': [{'@type': 'type.googleapis.com/google.rpc.Help', 'links': [{'description': 'Learn more about Gemini API quotas', 'url': 'https://ai.google.dev/gemini-api/docs/rate-limits'}]}, {'@type': 'type.googleapis.com/google.rpc.QuotaFailure', 'violations': [{'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerMinute-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerMinutePerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_requests', 'quotaId': 'GenerateRequestsPerDayPerProjectPerModel-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}, {'quotaMetric': 'generativelanguage.googleapis.com/generate_content_free_tier_input_token_count', 'quotaId': 'GenerateContentInputTokensPerModelPerDay-FreeTier', 'quotaDimensions': {'location': 'global', 'model': 'gemini-2.5-pro'}}]}, {'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '46s'}]}}

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
