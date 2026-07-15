from __future__ import annotations


class GenerationError(Exception):
    pass


class GenerationProviderNotFoundError(
    GenerationError,
):
    pass


class GenerationValidationError(
    GenerationError,
):
    pass


class GenerationExecutionError(
    GenerationError,
):
    pass


class PromptValidationError(
    GenerationError,
):
    pass


class OutputValidationError(
    GenerationError,
):
    pass


class GuardrailViolationError(
    GenerationError,
):
    pass
