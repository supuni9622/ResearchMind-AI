"""
System-wide generation-cost forecast (EVALUATION_IMPLEMENTATION_TRACKER.md
E18, EVALUATION_PLAN.md §11, PRODUCTION_READINESS_EVALUATION.md item 1
P2).

Deliberately cheap: a rolling-average daily rate projected across the
remaining days in the current month, derived entirely from the existing
`GenerationUsage` ledger -- not a novel forecasting model, per E18's own
scoping. Answers "at current burn rate, what will this month cost."

Distinct from `GenerationUsageService`/`GenerationUsageRepository.
summary_for_owner`, which report one user's own spend -- this is a
product-level, system-wide question, and this codebase has no
admin-authorization concept yet to gate a system-wide financial number
behind (checked: no `is_admin`/role-based dependency exists anywhere in
`apps/api/app`). Rather than invent one for a P2 item, this is exposed
as a runnable report (`python -m app.services.cost_forecast`), the
"scheduled report" half of E18's "dashboard panel or scheduled report"
acceptance criteria -- the dashboard-panel half is deferred to E7's
internal dashboard, which is where a real internal/admin-gated surface
belongs.
"""

from __future__ import annotations

import asyncio
import calendar
from datetime import UTC, date, datetime, timedelta

from pydantic import BaseModel

from app.repositories.generation_usage import GenerationUsageRepository

DEFAULT_TRAILING_WINDOW_DAYS = 14


class CostForecast(BaseModel):
    as_of: date

    month_to_date_cost_usd: float

    average_daily_cost_usd: float
    """Rolling average over `trailing_window_days`, treating a day with no
    recorded usage as $0 -- not just an average over days with activity."""

    trailing_window_days: int

    days_elapsed_in_month: int

    days_remaining_in_month: int

    projected_month_end_cost_usd: float
    """`month_to_date_cost_usd + average_daily_cost_usd * days_remaining_in_month`."""


def project_month_end_cost(
    daily_costs: list[tuple[date, float]],
    *,
    today: date,
    trailing_window_days: int = DEFAULT_TRAILING_WINDOW_DAYS,
) -> CostForecast:
    """
    Pure function, no I/O -- `daily_costs` is `(day, total_cost_usd)` pairs,
    typically from `GenerationUsageRepository.daily_cost_totals()`.
    """

    month_start = today.replace(day=1)
    month_to_date_cost = sum(cost for day, cost in daily_costs if month_start <= day <= today)

    window_start = today - timedelta(days=trailing_window_days - 1)
    trailing_cost = sum(cost for day, cost in daily_costs if window_start <= day <= today)
    average_daily_cost = trailing_cost / trailing_window_days if trailing_window_days else 0.0

    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day
    days_remaining = days_in_month - days_elapsed

    projected_month_end_cost = month_to_date_cost + average_daily_cost * days_remaining

    return CostForecast(
        as_of=today,
        month_to_date_cost_usd=round(month_to_date_cost, 4),
        average_daily_cost_usd=round(average_daily_cost, 4),
        trailing_window_days=trailing_window_days,
        days_elapsed_in_month=days_elapsed,
        days_remaining_in_month=days_remaining,
        projected_month_end_cost_usd=round(projected_month_end_cost, 4),
    )


async def compute_cost_forecast(
    repository: GenerationUsageRepository,
    *,
    today: date | None = None,
    trailing_window_days: int = DEFAULT_TRAILING_WINDOW_DAYS,
) -> CostForecast:
    """Fetches just enough ledger history (month-to-date + the trailing
    window, whichever reaches further back) and projects from it."""

    resolved_today = today or datetime.now(UTC).date()
    month_start = resolved_today.replace(day=1)
    window_start = resolved_today - timedelta(days=trailing_window_days - 1)
    lookback_start = min(month_start, window_start)
    since = _combine_utc(lookback_start)

    daily_costs = await repository.daily_cost_totals(since=since)
    return project_month_end_cost(
        daily_costs,
        today=resolved_today,
        trailing_window_days=trailing_window_days,
    )


def _combine_utc(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC)


if __name__ == "__main__":

    async def _main() -> None:
        from app.db.session import SessionFactory
        from app.repositories.generation_usage import GenerationUsageRepository

        async with SessionFactory() as session:
            forecast = await compute_cost_forecast(GenerationUsageRepository(session))

        print(f"As of {forecast.as_of}:")
        print(f"  Month-to-date cost:       ${forecast.month_to_date_cost_usd:.2f}")
        print(
            f"  Average daily cost (last {forecast.trailing_window_days}d): "
            f"${forecast.average_daily_cost_usd:.2f}"
        )
        print(f"  Days remaining in month:  {forecast.days_remaining_in_month}")
        print(f"  Projected month-end cost: ${forecast.projected_month_end_cost_usd:.2f}")

    asyncio.run(_main())
