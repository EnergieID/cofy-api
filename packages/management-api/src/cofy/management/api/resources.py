from __future__ import annotations

from typing import Annotated

from cofy.api import ResourceSettings
from cofy.api.references import references_in
from cofy.modules.discovery import discover_all_types
from fastapi import APIRouter, Path
from pydantic import BaseModel, Field

from ..errors import ResourceInUseError
from ..persitance.modules import ModulesPersistence
from ..persitance.resources import ResourcesPersistence
from .allowed_resources import allowed_resource_types

# Import every installed module/source/format type,
discover_all_types()
AnyResourceSettings = ResourceSettings.union_type()


class ModuleId(BaseModel):
    type: str
    name: str


class ResourceUsages(BaseModel):
    """What references a resource."""

    modules: list[ModuleId] = Field(description="The modules referencing the resource.")
    resources: list[str] = Field(description="The names of the resources referencing the resource.")

    @property
    def any(self) -> bool:
        return bool(self.modules or self.resources)


class ResourcesRouter:
    def __init__(self, persistence: ResourcesPersistence, modules: ModulesPersistence):
        self.persistence = persistence
        self.modules = modules
        self.router = APIRouter(prefix="/management/communities/{slug}/resources", tags=["Resources"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("", self.all, methods=["GET"])
        self.router.add_api_route("/{name}", self.get, methods=["GET"])
        self.router.add_api_route("/{name}/usages", self.usages, methods=["GET"])
        self.router.add_api_route("", self.create, methods=["POST"], status_code=201)
        self.router.add_api_route("/{name}", self.put, methods=["PUT"])
        self.router.add_api_route("/{name}", self.delete, methods=["DELETE"], status_code=204)

    def all(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> list[AnyResourceSettings]:
        return self.persistence.all(slug)

    def get(self, slug: str, name: str) -> AnyResourceSettings:
        return self.persistence.get(slug, name)

    def usages(self, slug: str, name: str) -> ResourceUsages:
        """What references this resource, and so keeps it from being deleted."""
        self.persistence.get(slug, name)  # a resource that doesn't exist has no usages to report
        return ResourceUsages(
            modules=[
                ModuleId(type=module.type, name=module.name)
                for module in self.modules.all(slug)
                if any(ref.name == name for ref in references_in(module))
            ],
            resources=[
                resource.name
                for resource in self.persistence.all(slug)
                if any(ref.name == name for ref in references_in(resource))
            ],
        )

    def create(self, slug: str, payload: AnyResourceSettings) -> AnyResourceSettings:
        self._check_type_is_allowed(slug, payload)
        return self.persistence.create(slug, payload)

    def put(self, slug: str, name: str, payload: AnyResourceSettings) -> AnyResourceSettings:
        if payload.name != name:
            raise ValueError(f"Resource name in body ({payload.name!r}) must match the URL path ({name!r})")
        self._check_type_is_allowed(slug, payload)
        return self.persistence.replace(slug, name, payload)

    def delete(self, slug: str, name: str) -> None:
        usages = self.usages(slug, name)
        if usages.any:
            users = [f"module {module.type}:{module.name}" for module in usages.modules] + [
                f"resource {resource}" for resource in usages.resources
            ]
            raise ResourceInUseError(f"Resource {name!r} is still referenced by {', '.join(users)}")
        self.persistence.delete(slug, name)
        return None

    @staticmethod
    def _check_type_is_allowed(slug: str, resource: AnyResourceSettings) -> None:
        """Reject a resource kind this community may not configure."""
        allowed = allowed_resource_types(slug)
        if resource.type not in allowed:
            raise ValueError(
                f"Resource type {resource.type!r} is not allowed for community {slug!r}. "
                f"Allowed types: {', '.join(sorted(allowed))}"
            )
