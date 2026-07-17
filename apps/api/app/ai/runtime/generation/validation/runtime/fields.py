from __future__ import annotations

from typing import Any

from pydantic import BaseModel

#
# `GenerationResult.parsed_output` is `Any` -- a runtime contract has no
# guarantee it's a specific Pydantic model (PRD §21's example is a bare
# dict). These helpers give the generic runtime validators (PRD §14) a
# single duck-typed way to read fields off either a `BaseModel`, a
# `dict`, or a plain list item, without each validator re-implementing
# the same isinstance checks.
#


def get_field(
    payload: Any,
    field: str,
) -> Any:
    if payload is None:
        return None

    if isinstance(payload, BaseModel):
        return getattr(
            payload,
            field,
            None,
        )

    if isinstance(payload, dict):
        return payload.get(
            field,
        )

    return getattr(
        payload,
        field,
        None,
    )


def get_list_field(
    payload: Any,
    field: str,
) -> list[Any]:
    value = get_field(
        payload,
        field,
    )

    return list(value) if isinstance(value, list) else []


def item_id(
    item: Any,
    *field_names: str,
) -> str | None:
    """
    Resolves an identifier off a list item that may itself just be a
    bare string id (e.g. `citations: ["S1", "S2"]`) or an
    object/dict carrying the id under one of `field_names`.
    """

    if isinstance(item, str):
        return item

    for field_name in field_names:
        value = get_field(
            item,
            field_name,
        )

        if isinstance(value, str):
            return value

    return None
