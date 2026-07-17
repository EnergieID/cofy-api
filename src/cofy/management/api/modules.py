from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Path

from cofy.api.module import ModuleSettings

from ..persitance.modules import ModulesPersistence

MODULE_SETTINGS_TYPE = ModuleSettings.union_type()


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
        slug: Annotated[str, Path(description="Community slug, currently one of: foo, bar")],
    ) -> list[MODULE_SETTINGS_TYPE]:
        return self.persistence.all(slug)

    def get(
        self,
        slug: str,
        module_type: str,
        name: str,
    ) -> MODULE_SETTINGS_TYPE:
        return self.persistence.get(slug, module_type, name)

    def create(
        self,
        slug: str,
        payload: Annotated[MODULE_SETTINGS_TYPE, Body(description="Full module settings payload")],
    ) -> MODULE_SETTINGS_TYPE:
        return self.persistence.create(slug, payload)

    def patch(
        self,
        slug: str,
        module_type: str,
        name: str,
        patch: Annotated[MODULE_SETTINGS_TYPE, Body(description="Partial module settings payload")],
    ) -> MODULE_SETTINGS_TYPE:
        original = self.persistence.get(slug, module_type, name)
        updated = original.model_copy(update=patch.model_dump(exclude_unset=True))
        return self.persistence.replace(slug, module_type, name, updated)

    def put(
        self,
        slug: str,
        module_type: str,
        name: str,
        payload: Annotated[MODULE_SETTINGS_TYPE, Body(description="Full module settings payload")],
    ) -> MODULE_SETTINGS_TYPE:
        return self.persistence.replace(slug, module_type, name, payload)

    def delete(
        self,
        slug: str,
        module_type: str,
        name: str,
    ) -> None:
        self.persistence.delete(slug, module_type, name)
        return None
