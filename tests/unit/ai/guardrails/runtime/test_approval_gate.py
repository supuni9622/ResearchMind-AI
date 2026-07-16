"""
No concrete ApprovalGateInterface implementation exists yet (see the
module docstring) -- these tests only round-trip the request/response
models.
"""

from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory
from app.ai.guardrails.runtime.approval_gate import ApprovalRequest, ApprovalResponse


def test_approval_request_defaults() -> None:
    request = ApprovalRequest(reason="high-cost tool call", category=GuardrailCategory.BUDGET)

    assert request.request_id is not None
    assert request.metadata == {}


def test_approval_response_round_trips_request_id() -> None:
    request = ApprovalRequest(reason="destructive action", category=GuardrailCategory.TOOL_POLICY)

    response = ApprovalResponse(request_id=request.request_id, approved=True, responder="alice")

    assert response.request_id == request.request_id
    assert response.approved is True
