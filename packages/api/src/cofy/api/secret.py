"""Secrets: credentials configured once in a community's secrets, and referenced by name wherever one is needed."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, SecretStr, SerializationInfo

from .references import NamedRef

NAME_PATTERN = r"^[a-zA-Z0-9_-]+$"


def _dump_value(value: SecretStr, info: SerializationInfo) -> str:
    # `round_trip=True` marks the serialization that is written to disk, the only place the value belongs.
    return value.get_secret_value() if info.round_trip else str(value)


SecretValue = Annotated[SecretStr, PlainSerializer(_dump_value, return_type=str, when_used="always")]
"""A secret's value itself, only revealed when its configuration is written to disk."""


class SecretSettings(BaseModel):
    """A named credential."""

    name: str = Field(description="The machine name of the secret, by which it is referenced.", pattern=NAME_PATTERN)
    description: str | None = Field(None, description="A short description of the secret.")
    value: SecretValue = Field(description="The secret itself.")

    def resolve(self) -> str:
        """The secret's actual value."""
        return self.value.get_secret_value()


def _secret_schema(schema: dict[str, Any]) -> None:
    # Marked for forms to offer the community's secrets, and without a title or description of its own, which would
    # stand in for those of the field it's in.
    schema.pop("title", None)
    schema.pop("description", None)
    schema["x-secret"] = True


class SecretRef(NamedRef):
    """A settings field holding a credential, as a reference to the secret holding it."""

    model_config = ConfigDict(json_schema_extra=_secret_schema)

    type: Literal["secret"] = "secret"
    name: str = Field(description="The name of the referenced secret.", pattern=NAME_PATTERN)


Secret = SecretRef
"""A settings field holding a credential, as a reference to the secret holding it."""
