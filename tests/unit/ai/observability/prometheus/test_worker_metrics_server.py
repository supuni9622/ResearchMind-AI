"""
Unit tests for `app/ai/observability/prometheus/create.py::start_worker_metrics_server()`
(E17 follow-up, 2026-08-12).

Only the disabled-Prometheus no-op path is unit-testable here without
opening a real socket -- the enabled path (`start_http_server()` binding
a real port) was verified live instead: a real `research_runtime_main`
process listening on its configured port, scraped successfully by a real
running Prometheus (`/api/v1/targets` reporting `health: up`).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.ai.observability.prometheus import create
from app.core.settings import settings


def test_start_worker_metrics_server_is_a_noop_when_prometheus_is_disabled(
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "prometheus_enabled", False)

    with patch("app.ai.observability.prometheus.create.start_http_server") as start_mock:
        create.start_worker_metrics_server(8010)

    start_mock.assert_not_called()


def test_start_worker_metrics_server_binds_the_given_port_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "prometheus_enabled", True)
    fake_registry = MagicMock()
    monkeypatch.setattr(
        create, "get_prometheus_metric_registry", lambda: MagicMock(registry=fake_registry)
    )

    with patch("app.ai.observability.prometheus.create.start_http_server") as start_mock:
        create.start_worker_metrics_server(8010)

    start_mock.assert_called_once_with(8010, registry=fake_registry)
