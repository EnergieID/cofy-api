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

    def put(
        self,
        slug: str,
        module_type: str,
        name: str,
        payload: Annotated[AnyModuleSettings, Body(description="Full module settings payload")],
    ) -> AnyModuleSettings:
        self._check_identity_matches_path(payload, module_type, name)
        return self.persistence.replace(slug, module_type, name, payload)

    @staticmethod
    def _check_identity_matches_path(module: AnyModuleSettings, module_type: str, name: str) -> None:
        """Reject a PUT body whose (type, name) differs from the URL it was sent to."""
        if (module.type, module.name) != (module_type, name):
            raise ValueError(
                f"Module identity in body (type={module.type!r}, name={module.name!r}) must match "
                f"the URL path (type={module_type!r}, name={name!r})"
            )

    def delete(
        self,
        slug: str,
        module_type: str,
        name: str,
    ) -> None:
        self.persistence.delete(slug, module_type, name)
        return None
