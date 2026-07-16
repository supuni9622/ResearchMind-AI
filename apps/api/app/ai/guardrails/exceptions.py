"""
Guardrails exceptions.
"""


class GuardrailError(Exception):
    """Base exception for the Guardrails Platform."""


class GuardrailProviderNotFoundError(GuardrailError):
    """Raised when a registry lookup finds no provider/check registered."""


class GuardrailPolicyError(GuardrailError):
    """Raised when a policy configuration is invalid."""
