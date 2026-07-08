# ResearchMind Ingestion Benchmark

**Date:** 2026-07-08T08:31:16.092182+00:00
**Commit:** `e7a6ddf`

## Environment

| Key | Value |
|---|---|
| Python Version | 3.12.13 |
| Platform | macOS-26.5.2-arm64-arm-64bit |
| Chunking Strategy | markdown |
| Embedding Provider | voyage_ai |
| Vector Store Provider | qdrant |
| Owner Id | benchmark-ingestion-pipeline |
| Embedding Model | voyage-3-lite |
| Qdrant Collection | researchmind_knowledge |

## Dataset

- **Name:** research-papers
- **Directory:** `benchmarks/datasets/research-papers`
- **Documents:** 5
- **Note:** documents were loaded from pre-processed `processed_document.json` artifacts. Upload and Processing (PDF parsing) were not re-executed; 'File Size' reflects the size of that source JSON, not the original PDF.

### Dataset Summary

| Metric | Total | Average per Document |
|---|---:|---:|
| Pages | 118 | 23.6 |
| Characters | 498,683 | 99,737 |
| Words | 66,624 | 13,325 |

## Individual Document Results

| Document | Pages | Chars | Words | Chunks | Avg Chunk | Largest | Smallest | Chunking (ms) | Embeddings | Dims | Embedding (ms) | Vectors | Indexing (ms) | Collection | Total (ms) | Peak Mem (MB) | Artifact Size |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|
| 151__CRC.pdfrevised.pdf | 11 | 22,201 | 3,024 | 62 | 373 | 499 | 40 | 1.8 | 62 | 512 | 2483.7 | 62 | 1422.9 | researchmind_knowledge | 8578.0 | 544.9 | 1.17 MB |
| LLM_RESEARCH.pdf | 47 | 345,335 | 45,514 | 999 | 351 | 499 | 1 | 37.1 | 999 | 512 | 20710.7 | 999 | 1583.6 | researchmind_knowledge | 65520.6 | 561.7 | 18.65 MB |
| Noise_is_Signal_Density-Based_Outliers_as_Leading_.pdf | 10 | 41,483 | 6,129 | 130 | 342 | 499 | 12 | 3.4 | 130 | 512 | 3342.4 | 130 | 1314.9 | researchmind_knowledge | 14114.0 | 423.4 | 2.43 MB |
| Loop_Engineering_Revised.pdf | 36 | 78,455 | 10,376 | 252 | 334 | 499 | 3 | 11.1 | 252 | 512 | 5920.7 | 252 | 1447.0 | researchmind_knowledge | 22043.3 | 422.4 | 4.70 MB |
| data engineering .pdf | 14 | 11,209 | 1,581 | 57 | 230 | 499 | 11 | 3.3 | 57 | 512 | 20827.5 | 57 | 1286.7 | researchmind_knowledge | 33190.9 | 422.4 | 1.04 MB |

## Aggregate Statistics

| Metric | Average | Minimum | Maximum | Median | P95 |
|---|---:|---:|---:|---:|---:|
| Chunk Count | 300.0 | 57.0 | 999.0 | 130.0 | 849.6 |
| Embedding Count | 300.0 | 57.0 | 999.0 | 130.0 | 849.6 |
| Artifact Size (bytes) | 5869540.2 | 1091679.0 | 19559986.0 | 2549630.0 | 16632612.4 |

## Pipeline Timing

| Stage | Average (ms) | Minimum | Maximum | Median | P95 |
|---|---:|---:|---:|---:|---:|
| Total Pipeline | 28689.4 | 8578.0 | 65520.6 | 22043.3 | 59054.6 |
| Processing (skipped) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| Chunking | 11.4 | 1.8 | 37.1 | 3.4 | 31.9 |
| Embedding | 10657.0 | 2483.7 | 20827.5 | 5920.7 | 20804.1 |
| Indexing | 1411.0 | 1286.7 | 1583.6 | 1422.9 | 1556.3 |

## Storage Report

| Metric | Value |
|---|---:|
| Average storage per document | 5.60 MB |
| Average storage per chunk | 1.66 KB |
| Average storage per embedding | 16.79 KB |
| Total storage generated | 27.99 MB |
| Avg processed_document.json | 198.18 KB |
| Avg chunks.json | 496.69 KB |
| Avg embeddings.json | 4.92 MB |
| Avg indexing.json | 562.60 B |

## Throughput

| Metric | Value |
|---|---:|
| Documents / minute | 2.09 |
| Chunks / second | 10.46 |
| Embeddings / second | 10.46 |
| Vectors / second | 10.46 |

## Memory Usage

| Metric | Value (MB) |
|---|---:|
| Average peak memory | 475.0 |
| Minimum peak memory | 422.4 |
| Maximum peak memory | 561.7 |

## Success Report

| Metric | Value |
|---|---:|
| Documents processed | 5 |
| Successful | 5 |
| Failed | 0 |
| Success Rate | 100% |

## Observations

- **Slowest document:** LLM_RESEARCH.pdf (65.52s)
- **Fastest document:** 151__CRC.pdfrevised.pdf (8.58s)
- **Largest artifact:** LLM_RESEARCH.pdf / embeddings.json (16.37 MB)
- **Smallest artifact:** data engineering .pdf / indexing.json (547.00 B)
- **Average pipeline time:** 28.69s
- **Average vectors generated:** 300
- **Average chunks generated:** 300

## Production Readiness

✔ Complete ingestion pipeline functional
✔ 5/5 documents successfully processed
✔ 100% embedding success
✔ 100% indexing success
✔ All artifacts generated
✔ Average pipeline time: 28.69 s
✔ Average vectors indexed: 300
✔ No failures observed

### Recommendations

- Optimize embedding latency (largest contributor)
- Artifact storage per document is large; consider compression.
- Ready to proceed to Retrieval Platform

