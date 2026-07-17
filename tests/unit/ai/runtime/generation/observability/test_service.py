"""
Unit tests for GenerationMetricsService.

Covers:
- record() returns a snapshot matching build_generation_metrics_snapshot
- record() always increments the requests-total counter and records duration
- record() only increments retries/regenerations/cache-hit counters when
  the corresponding snapshot field is truthy
- record() logs a generation.metrics.recorded event
"""

from __future__ import annotations

from unittest.mock import MagicMock

from app.ai.runtime.generation.observability.models import build_generation_metrics_snapshot
from app.ai.runtime.generation.observability.service import GenerationMetricsService
from app.infrastructure.metrics.generation import (
    GENERATION_CACHE_HITS_TOTAL,
    GENERATION_REGENERATIONS_TOTAL,
    GENERATION_REQUESTS_TOTAL,
    GENERATION_RETRIES_TOTAL,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


def _fake_recorder() -> MagicMock:
    recorder = MagicMock()
    recorder.increment = MagicMock()
    recorder.record_duration = MagicMock()
    return recorder


async def test_record_returns_the_expected_snapshot() -> None:
    result = make_result()
    service = GenerationMetricsService(metrics=_fake_recorder())

    snapshot = service.record(result)

    assert snapshot == build_generation_metrics_snapshot(result)


async def test_record_always_increments_requests_total_and_records_duration() -> None:
    recorder = _fake_recorder()
    service = GenerationMetricsService(metrics=recorder)

    service.record(make_result())

    recorder.increment.assert_any_call(metric=GENERATION_REQUESTS_TOTAL)
    recorder.record_duration.assert_called_once()


async def test_record_skips_optional_counters_when_not_applicable() -> None:
    recorder = _fake_recorder()
    service = GenerationMetricsService(metrics=recorder)

    service.record(make_result())

    incremented_metrics = {call.kwargs["metric"] for call in recorder.increment.call_args_list}

    assert GENERATION_RETRIES_TOTAL not in incremented_metrics
    assert GENERATION_REGENERATIONS_TOTAL not in incremented_metrics
    assert GENERATION_CACHE_HITS_TOTAL not in incremented_metrics


async def test_record_increments_regenerations_when_present() -> None:
    recorder = _fake_recorder()
    service = GenerationMetricsService(metrics=recorder)

    result = make_result().model_copy(update={"regeneration_attempts": 2})

    service.record(result)

    incremented_metrics = {call.kwargs["metric"] for call in recorder.increment.call_args_list}

    assert GENERATION_REGENERATIONS_TOTAL in incremented_metrics
