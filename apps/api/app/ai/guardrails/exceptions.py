"""
Guardrails exceptions.
"""


class GuardrailError(Exception):
    """Base exception for the Guardrails Platform."""


class GuardrailProviderNotFoundError(GuardrailError):
    """Raised when a registry lookup finds no provider/check registered."""


class GuardrailPolicyError(GuardrailError):
    """Raised when a policy configuration is invalid."""


class GuardrailBlockedError(GuardrailError):
    """
    Raised by a caller (e.g. `ContextBuilderService`) when a
    `GuardrailResult` comes back `blocked=True` and the caller has no
    finer-grained recovery than aborting the pipeline outright --
    PRD §8 "Blocked retrieval must stop downstream generation".
    """
