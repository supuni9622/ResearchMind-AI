"""
Unit tests for app/services/cost_forecast.py (E18).

`project_month_end_cost` is pure -- no mocking needed. `compute_cost_forecast`
is tested against a `MagicMock` repository (no real DB call), matching the
project's convention of mocking at the repository boundary for unit tests
(see tests/unit/repositories/test_generation_usage.py) -- the real
date-grouping SQL itself is covered by
tests/integration/test_generation_usage_repository.py's
test_daily_cost_totals_* tests.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.cost_forecast import compute_cost_forecast, project_month_end_cost


def test_projects_month_end_cost_from_month_to_date_plus_trailing_average() -> None:
    daily_costs = [
        (date(2026, 1, 1), 10.0),
        (date(2026, 1, 2), 10.0),
        (date(2026, 1, 3), 10.0),
        (date(2026, 1, 4), 10.0),
    ]

    forecast = project_month_end_cost(daily_costs, today=date(2026, 1, 4), trailing_window_days=4)

    assert forecast.month_to_date_cost_usd == pytest.approx(40.0)
    assert forecast.average_daily_cost_usd == pytest.approx(10.0)
    assert forecast.days_elapsed_in_month == 4
    assert forecast.days_remaining_in_month == 27  # January has 31 days
    # 40 month-to-date + 10/day * 27 remaining days
    assert forecast.projected_month_end_cost_usd == pytest.approx(310.0)


def test_treats_days_with_no_recorded_usage_as_zero_in_the_average() -> None:
    """Only 2 of a 4-day trailing window have any usage -- the average
    must still divide by the full window, not just the days with data,
    or a quiet weekend would inflate the projected rate."""

    daily_costs = [
        (date(2026, 1, 3), 8.0),
        (date(2026, 1, 4), 8.0),
    ]

    forecast = project_month_end_cost(daily_costs, today=date(2026, 1, 4), trailing_window_days=4)

    assert forecast.average_daily_cost_usd == pytest.approx(4.0)  # 16 / 4, not 16 / 2


def test_ignores_costs_outside_the_trailing_window_for_the_average() -> None:
    daily_costs = [
        (date(2025, 12, 1), 1000.0),  # far outside any window, must not leak in
        (date(2026, 1, 4), 10.0),
    ]

    forecast = project_month_end_cost(daily_costs, today=date(2026, 1, 4), trailing_window_days=2)

    assert forecast.average_daily_cost_usd == pytest.approx(5.0)  # 10 / 2


def test_ignores_costs_after_today_for_month_to_date() -> None:
    daily_costs = [
        (date(2026, 1, 4), 10.0),
        (date(2026, 1, 10), 999.0),  # future relative to `today`, must not count
    ]

    forecast = project_month_end_cost(daily_costs, today=date(2026, 1, 4), trailing_window_days=4)

    assert forecast.month_to_date_cost_usd == pytest.approx(10.0)


def test_projects_zero_when_no_usage_recorded_at_all() -> None:
    forecast = project_month_end_cost([], today=date(2026, 1, 15), trailing_window_days=14)

    assert forecast.month_to_date_cost_usd == 0.0
    assert forecast.average_daily_cost_usd == 0.0
    assert forecast.projected_month_end_cost_usd == 0.0


def test_days_remaining_is_zero_on_the_last_day_of_the_month() -> None:
    forecast = project_month_end_cost(
        [(date(2026, 2, 28), 5.0)], today=date(2026, 2, 28), trailing_window_days=1
    )

    assert forecast.days_remaining_in_month == 0
    assert forecast.projected_month_end_cost_usd == pytest.approx(5.0)


async def test_compute_cost_forecast_queries_since_the_earlier_of_month_start_or_window_start() -> (
    None
):
    repository = MagicMock()
    repository.daily_cost_totals = AsyncMock(return_value=[])

    await compute_cost_forecast(
        repository,
        today=date(2026, 1, 5),
        trailing_window_days=14,
    )

    repository.daily_cost_totals.assert_awaited_once()
    since = repository.daily_cost_totals.await_args.kwargs["since"]
    # trailing window (14 days back from Jan 5) reaches into December,
    # further back than the month start (Jan 1) -- must use the earlier one.
    assert since == datetime(2025, 12, 23, tzinfo=UTC)


async def test_compute_cost_forecast_defaults_to_todays_date(monkeypatch) -> None:
    repository = MagicMock()
    repository.daily_cost_totals = AsyncMock(return_value=[])

    forecast = await compute_cost_forecast(repository)

    assert forecast.as_of == datetime.now(UTC).date()
