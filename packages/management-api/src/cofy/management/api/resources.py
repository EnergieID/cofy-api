from __future__ import annotations

from typing import Annotated

from cofy.api import ResourceSettings
from cofy.modules.discovery import discover_all_types
from fastapi import Path

from ..auth.access import Subject
from ..persitance.modules import ModulesPersistence
from ..persitance.resources import ResourcesPersistence
from ..policies.policy import Policy, PolicyRouter
from .allowed_resources import allowed_resource_types
from .in_use import check_unused

# Import every installed module/source/format type,
discover_all_types()
AnyResourceSettings = ResourceSettings.union_type()


class ResourcesRouter:
    def __init__(self, persistence: ResourcesPersistence, modules: ModulesPersistence):
        self.persistence = persistence
        self.modules = modules
        self.router = PolicyRouter(
            subject=Subject.resources, prefix="/management/communities/{slug}/resources", tags=["Resources"]
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("", self.all, methods=["GET"], rule=Policy.all)
        self.router.add_api_route("/{name}", self.get, methods=["GET"], rule=Policy.get)
        self.router.add_api_route("", self.create, methods=["POST"], rule=Policy.create, status_code=201)
        self.router.add_api_route("/{name}", self.put, methods=["PUT"], rule=Policy.put)
        self.router.add_api_route("/{name}", self.delete, methods=["DELETE"], rule=Policy.delete, status_code=204)

    def all(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> list[AnyResourceSettings]:
        return self.persistence.all(slug)

    def get(self, slug: str, name: str) -> AnyResourceSettings:
        return self.persistence.get(slug, name)

    def create(self, slug: str, payload: AnyResourceSettings) -> AnyResourceSettings:
        self._check_type_is_allowed(slug, payload)
        return self.persistence.create(slug, payload)

    def put(self, slug: str, name: str, payload: AnyResourceSettings) -> AnyResourceSettings:
        if payload.name != name:
            raise ValueError(f"Resource name in body ({payload.name!r}) must match the URL path ({name!r})")
        self._check_type_is_allowed(slug, payload)
        return self.persistence.replace(slug, name, payload)

    def delete(self, slug: str, name: str) -> None:
        self.persistence.get(slug, name)
        check_unused("resource", name, self.modules.all(slug), self.persistence.all(slug))
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
