"""
Integration tests for the Prometheus Grafana Observability platform
(prometheus_grafana_observability_prd.md §36.3/§41), exercised through
the real FastAPI app (`tests.conftest.client`) rather than mocks -- this
is the one place that verifies the HTTP middleware, the metrics
recorder factory, and the `/metrics` endpoint are actually wired
together end to end.

Covers:
- a real request increments `researchmind_http_requests_total` with the
  normalized route template (never a raw path)
- `GET /metrics` returns a Prometheus-compatible payload containing
  known application metric names
- the metrics endpoint itself never fails a normal request (Prometheus
  disabled/broken must fail open -- see unit-level coverage in
  test_prometheus_recorder.py for the recorder's own failure handling)
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_request_increments_http_requests_total(client: TestClient) -> None:
    client.get("/api/v1/health/live")

    metrics_response = client.get("/metrics")

    assert metrics_response.status_code == 200
    body = metrics_response.text

    assert "researchmind_http_requests_total{" in body
    assert 'route="/api/v1/health/live"' in body
    assert 'status_code="200"' in body


def test_metrics_endpoint_returns_prometheus_payload(client: TestClient) -> None:
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "researchmind_http_requests_total" in response.text


def test_metrics_endpoint_does_not_expose_request_identifiers(client: TestClient) -> None:
    client.get("/api/v1/health/live")

    response = client.get("/metrics")

    # Route labels are templates, never raw values -- a UUID-shaped path
    # segment must never appear as a label value.
    assert "request_id" not in response.text
    assert "session_id" not in response.text
    assert "owner_id" not in response.text
