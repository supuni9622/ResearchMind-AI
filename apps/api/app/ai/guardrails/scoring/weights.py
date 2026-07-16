from __future__ import annotations

#
# PRD §13 weights: overall_risk = input*0.30 + retrieval*0.30 +
# generation*0.20 + runtime*0.20. Configurable — this is just the
# default table `compute_overall_risk` renormalizes over.
#

STAGE_WEIGHTS: dict[str, float] = {
    "input": 0.30,
    "retrieval": 0.30,
    "generation": 0.20,
    "runtime": 0.20,
}
