"""CRUD over a community's secrets, which are written but never read back."""

from __future__ import annotations

from typing import Annotated

from cofy.api import SecretSettings
from cofy.api.secret import NAME_PATTERN
from fastapi import Path
from pydantic import BaseModel, Field

from ..auth.access import Subject
from ..persitance.modules import ModulesPersistence
from ..persitance.resources import ResourcesPersistence
from ..persitance.secrets import SecretsPersistence
from ..policies.policy import Policy, PolicyRouter
from .in_use import check_unused


class SecretBody(BaseModel):
    """A secret as written: its value is replaced on every write."""

    name: str = Field(description="The machine name of the secret, by which it is referenced.", pattern=NAME_PATTERN)
    description: str | None = Field(None, description="A short description of the secret.")
    value: str = Field(description="The secret itself.")

    def to_settings(self) -> SecretSettings:
        return SecretSettings.model_validate(self.model_dump())


class SecretInfo(BaseModel):
    """A secret as reported: everything but its value."""

    name: str
    description: str | None = None

    @classmethod
    def of(cls, secret: SecretSettings) -> SecretInfo:
        return cls(name=secret.name, description=secret.description)


class SecretsRouter:
    def __init__(self, persistence: SecretsPersistence, modules: ModulesPersistence, resources: ResourcesPersistence):
        self.persistence = persistence
        self.modules = modules
        self.resources = resources
        self.router = PolicyRouter(
            subject=Subject.secrets, prefix="/management/communities/{slug}/secrets", tags=["Secrets"]
        )
        self.router.add_api_route("", self.all, methods=["GET"], rule=Policy.all)
        self.router.add_api_route("/{name}", self.get, methods=["GET"], rule=Policy.get)
        self.router.add_api_route("", self.create, methods=["POST"], rule=Policy.create, status_code=201)
        self.router.add_api_route("/{name}", self.put, methods=["PUT"], rule=Policy.put)
        self.router.add_api_route("/{name}", self.delete, methods=["DELETE"], rule=Policy.delete, status_code=204)

    def all(self, slug: Annotated[str, Path(description="Community slug")]) -> list[SecretInfo]:
        return [SecretInfo.of(secret) for secret in self.persistence.all(slug)]

    def get(self, slug: str, name: str) -> SecretInfo:
        return SecretInfo.of(self.persistence.get(slug, name))

    def create(self, slug: str, payload: SecretBody) -> SecretInfo:
        return SecretInfo.of(self.persistence.create(slug, payload.to_settings()))

    def put(self, slug: str, name: str, payload: SecretBody) -> SecretInfo:
        if payload.name != name:
            raise ValueError(f"Secret name in body ({payload.name!r}) must match the URL path ({name!r})")
        return SecretInfo.of(self.persistence.replace(slug, name, payload.to_settings()))

    def delete(self, slug: str, name: str) -> None:
        self.persistence.get(slug, name)
        check_unused("secret", name, self.modules.all(slug), self.resources.all(slug))
        self.persistence.delete(slug, name)
        return None
