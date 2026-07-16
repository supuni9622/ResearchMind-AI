from __future__ import annotations


def estimate_cost(
    *,
    prompt_tokens: int,
    completion_tokens: int,
    input_cost_per_1m: float,
    output_cost_per_1m: float,
) -> float:

    input_cost = (prompt_tokens / 1_000_000) * input_cost_per_1m

    output_cost = (completion_tokens / 1_000_000) * output_cost_per_1m

    return input_cost + output_cost
