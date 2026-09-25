"""A credential field that is masked over HTTP but round-trips to persistence intact."""

from typing import Annotated, Any

from pydantic import BaseModel, PlainSerializer, SecretStr, SerializationInfo

MASK = "**********"
"""Placeholder serialized in place of a secret's value. Sent back unchanged, it means "keep
the stored value"."""


def _dump_secret(value: SecretStr, info: SerializationInfo) -> str:
    # `round_trip=True` marks a serialization whose output is fed back into validation, which
    # is how community YAML is rewritten and the only place the real value belongs.
    return value.get_secret_value() if info.round_trip else MASK


Secret = Annotated[SecretStr, PlainSerializer(_dump_secret, return_type=str, when_used="always")]
"""A settings field holding a credential.

Validates from a plain string, serializes to `MASK` everywhere except the persistence round
trip, and carries `format: password` and `writeOnly: true` into the JSON Schema.
"""


def restore_masked_secrets(incoming: Any, stored: Any) -> None:
    """Copy secrets from *stored* onto any `MASK` placeholder in *incoming*, in place.

    Only substitutes where the two shapes agree, so switching a polymorphic branch restores
    nothing and the incoming values stand as sent. List elements are paired by position.
    """
    if isinstance(incoming, BaseModel) and isinstance(stored, BaseModel):
        # A field name matching by coincidence across unrelated concrete classes (two source
        # types both happening to have an `api_key`) is not "the same shape" - restoring across
        # that would leak one service's credential onto another, so the classes must match too.
        if type(incoming) is not type(stored):
            return
        # Same concrete class, so every name in `model_fields` is guaranteed to be a present
        # attribute on both - no `hasattr` guard needed here the way the dict/list cases below
        # need one, since those pair up by key/position instead of by a shared class.
        for name in type(incoming).model_fields:
            new_value, old_value = getattr(incoming, name), getattr(stored, name)
            if isinstance(new_value, SecretStr) and isinstance(old_value, SecretStr):
                if new_value.get_secret_value() == MASK:
                    setattr(incoming, name, old_value)
            else:
                restore_masked_secrets(new_value, old_value)

    elif isinstance(incoming, list) and isinstance(stored, list):
        for new_item, old_item in zip(incoming, stored, strict=False):
            restore_masked_secrets(new_item, old_item)

    elif isinstance(incoming, dict) and isinstance(stored, dict):
        for key, new_value in incoming.items():
            if key in stored:
                restore_masked_secrets(new_value, stored[key])
