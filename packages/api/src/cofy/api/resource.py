"""Named resources: values configured once and referenced from anywhere in a configuration."""

from typing import Any, Literal

from pydantic import Field

from .from_settings_mixin import BaseSettingsModel, FromSettingsMixin
from .secret import SecretValue


class ResourceSettings(BaseSettingsModel):
    type: Literal["resource"] = "resource"
    name: str = Field(
        description="The machine name of the resource, by which it is referenced. No spaces, no special characters.",
        pattern=r"^[a-zA-Z0-9_-]+$",
    )
    description: str | None = Field(None, description="A short description of the resource.")


class Resource(FromSettingsMixin, settings=ResourceSettings, abstract=True):
    """A named value that can be referenced from anywhere in a configuration."""

    def __init__(self, name: str, value: Any, description: str | None = None):
        self.name = name
        self.value = value
        self.description = description


class SecretResourceSettings(ResourceSettings):
    type: Literal["secret"] = "secret"
    value: SecretValue


class SecretResource(Resource, settings=SecretResourceSettings):
    """A credential."""
