"""Online risk-weighted scoring (EVALUATION_PLAN.md §14, E5).

Scores production traffic against the merged sampling table §14
specifies: free deterministic checks run on every answer-producing
generation, LLM-judge metrics run on a risk-weighted sample (always for
guardrail-flagged requests and non-`PASS` Deep Research review decisions,
oversampled under a config-fingerprint canary window, a flat baseline
rate otherwise).
"""

from __future__ import annotations
