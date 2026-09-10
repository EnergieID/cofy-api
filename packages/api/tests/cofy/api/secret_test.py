"""Unit tests for the `Secret` field type and its masked-write merge."""

from typing import Literal

import pytest
from pydantic import BaseModel, SecretStr

from cofy.api.secret import MASK, Secret, restore_masked_secrets


class Credentials(BaseModel):
    api_key: Secret
    label: str = "unnamed"


class Wrapper(BaseModel):
    creds: Credentials
    note: str | None = None


# ── serialization ─────────────────────────────────────────────────────────


def test_dump_masks_the_secret_by_default():
    assert Credentials(api_key="real").model_dump()["api_key"] == MASK


def test_dump_reveals_the_secret_for_a_persistence_round_trip():
    assert Credentials(api_key="real").model_dump(round_trip=True)["api_key"] == "real"


def test_masked_dump_is_json_serializable():
    """A plain `SecretStr` dumps to an object yaml/json cannot represent; `Secret` must not."""
    assert Credentials(api_key="real").model_dump(mode="json")["api_key"] == MASK


def test_schema_marks_the_field_as_a_write_only_password():
    field = Credentials.model_json_schema()["properties"]["api_key"]
    assert field["type"] == "string"
    assert field["format"] == "password"
    assert field["writeOnly"] is True


def test_repr_does_not_leak_the_secret():
    assert "real" not in repr(Credentials(api_key="real"))


# ── restore_masked_secrets ────────────────────────────────────────────────


def test_masked_secret_is_replaced_by_the_stored_one():
    incoming = Credentials(api_key=MASK, label="edited")
    restore_masked_secrets(incoming, Credentials(api_key="stored"))

    assert incoming.api_key.get_secret_value() == "stored"
    assert incoming.label == "edited"  # the rest of the payload is untouched


def test_a_real_incoming_secret_is_left_alone():
    incoming = Credentials(api_key="rotated")
    restore_masked_secrets(incoming, Credentials(api_key="stored"))

    assert incoming.api_key.get_secret_value() == "rotated"


def test_restores_through_nested_models():
    incoming = Wrapper(creds=Credentials(api_key=MASK), note="hi")
    restore_masked_secrets(incoming, Wrapper(creds=Credentials(api_key="stored")))

    assert incoming.creds.api_key.get_secret_value() == "stored"


def test_restores_through_lists_pairwise():
    incoming = [Credentials(api_key=MASK), Credentials(api_key=MASK)]
    stored = [Credentials(api_key="first"), Credentials(api_key="second")]
    restore_masked_secrets(incoming, stored)

    assert [c.api_key.get_secret_value() for c in incoming] == ["first", "second"]


def test_extra_list_entries_are_left_as_sent():
    """A longer incoming list keeps its own values rather than erroring."""
    incoming = [Credentials(api_key=MASK), Credentials(api_key="new")]
    restore_masked_secrets(incoming, [Credentials(api_key="first")])

    assert incoming[0].api_key.get_secret_value() == "first"
    assert incoming[1].api_key.get_secret_value() == "new"


def test_restores_through_dicts_by_key():
    incoming = {"a": Credentials(api_key=MASK), "b": Credentials(api_key=MASK)}
    stored = {"a": Credentials(api_key="stored-a")}
    restore_masked_secrets(incoming, stored)

    assert incoming["a"].api_key.get_secret_value() == "stored-a"
    assert incoming["b"].api_key.get_secret_value() == MASK  # no counterpart to restore from


def test_field_absent_from_the_stored_model_is_skipped():
    class Fewer(BaseModel):
        label: str = "unnamed"

    incoming = Credentials(api_key=MASK)
    restore_masked_secrets(incoming, Fewer())

    assert incoming.api_key.get_secret_value() == MASK


def test_mismatched_shapes_restore_nothing():
    """Swapping a polymorphic branch must leave the incoming payload exactly as sent."""

    class OtherCredentials(BaseModel):
        type: Literal["other"] = "other"
        token: Secret

    incoming = OtherCredentials(token=MASK)
    restore_masked_secrets(incoming, Credentials(api_key="stored"))

    assert incoming.token.get_secret_value() == MASK


def test_non_model_values_are_ignored():
    """Scalars and mismatched container kinds are a no-op rather than an error."""
    restore_masked_secrets("a string", 42)
    restore_masked_secrets([Credentials(api_key=MASK)], {"not": "a list"})


# ── integration with the settings -> object conversion ────────────────────


def test_settings_conversion_hands_the_runtime_a_plain_string():
    """`FromSettingsMixin` must unwrap secrets so constructors keep their `str` signatures."""
    from cofy.api.from_settings_mixin import _resolve

    resolved = _resolve(SecretStr("real"))

    assert resolved == "real"
    assert isinstance(resolved, str)
    assert not isinstance(resolved, SecretStr)


@pytest.mark.parametrize("value", ["", MASK, "real"])
def test_any_string_validates_into_a_secret(value: str):
    """Config files and request bodies need no special syntax for a secret field."""
    assert Credentials(api_key=value).api_key.get_secret_value() == value
