from __future__ import annotations

from app.ai.guardrails.enums import GuardrailSeverity

#
# Runtime budget defaults (PRD §11). `None` on a `BudgetPolicy` field means
# "unbounded" — these are only the defaults `create.py` wires up, not hard
# limits baked into the guardrail logic itself.
#

DEFAULT_MAX_TOKENS = 100_000

DEFAULT_MAX_COST_USD = 5.0

DEFAULT_MAX_TOOL_CALLS = 50

DEFAULT_MAX_ITERATIONS = 25

DEFAULT_MAX_RUNTIME_SECONDS = 300.0

BUDGET_WARN_MARGIN = 0.9
"""Warn once usage reaches this fraction of a budget limit, mirrors
`validation/input/token_budget.py`'s `_WARN_UTILIZATION`."""

#
# Stage risk scoring (PRD §13). A `GuardrailResult.score` is the max of
# every issue's severity score in that stage — deliberately max, not mean,
# so one CRITICAL issue can't be diluted by several INFO ones.
#

SEVERITY_RISK_SCORES: dict[GuardrailSeverity, float] = {
    GuardrailSeverity.INFO: 0.0,
    GuardrailSeverity.WARNING: 0.3,
    GuardrailSeverity.ERROR: 0.7,
    GuardrailSeverity.CRITICAL: 1.0,
}

#
# Retrieval-stage thresholds
#

LOW_TRUST_THRESHOLD = 0.5
"""Below this `SourceTrust.trust_score`, `retrieval/source_trust.py` warns."""

#
# Generation-stage thresholds
#

FAITHFULNESS_THRESHOLD = 0.3
"""Below this groundedness score, `generation/faithfulness.py` warns.
Matches `validation/output/hallucination_validator.py`'s
`_LOW_GROUNDEDNESS_THRESHOLD` so the two platforms agree on what "low"
means for the same underlying signal."""
