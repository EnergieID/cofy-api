from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Path

from cofy.api.module import ModuleSettings
from cofy.modules.discovery import discover_all_types

from ..persitance.modules import ModulesPersistence

# Import every installed module/source/format type,
discover_all_types()
AnyModuleSettings = ModuleSettings.union_type()


class ModulesRouter:
    def __init__(self, persitance: ModulesPersistence):
        self.persistence = persitance
        self.router = APIRouter(prefix="/management/communities/{slug}/modules", tags=["Modules"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("", self.all, methods=["GET"])
        self.router.add_api_route("/{module_type}/{name}", self.get, methods=["GET"])
        self.router.add_api_route("", self.create, methods=["POST"], status_code=201)
        self.router.add_api_route("/{module_type}/{name}", self.patch, methods=["PATCH"])
        self.router.add_api_route("/{module_type}/{name}", self.put, methods=["PUT"])
        self.router.add_api_route("/{module_type}/{name}", self.delete, methods=["DELETE"], status_code=204)

    def all(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> list[AnyModuleSettings]:
        return self.persistence.all(slug)

    def get(
        self,
        slug: str,
        module_type: str,
        name: str,
    ) -> AnyModuleSettings:
        return self.persistence.get(slug, module_type, name)

    def create(
        self,
        slug: str,
        payload: Annotated[AnyModuleSettings, Body(description="Full module settings payload")],
    ) -> AnyModuleSettings:
        return self.persistence.create(slug, payload)

    def patch(
        self,
        slug: str,
        module_type: str,
        name: str,
        patch: Annotated[AnyModuleSettings, Body(description="Partial module settings payload")],
    ) -> AnyModuleSettings:
        original = self.persistence.get(slug, module_type, name)
        updated = original.model_copy(update=patch.model_dump(exclude_unset=True))
        return self.persistence.replace(slug, module_type, name, updated)

    def put(
        self,
        slug: str,
        module_type: str,
        name: str,
        payload: Annotated[AnyModuleSettings, Body(description="Full module settings payload")],
    ) -> AnyModuleSettings:
        return self.persistence.replace(slug, module_type, name, payload)

    def delete(
        self,
        slug: str,
        module_type: str,
        name: str,
    ) -> None:
        self.persistence.delete(slug, module_type, name)
        return None
