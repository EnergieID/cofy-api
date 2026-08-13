from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Path
from pydantic import TypeAdapter

from cofy.api.module import ModuleSettings
from cofy.modules.billing import BillingModuleSettings  # noqa: F401
from cofy.modules.tariff import (  # noqa: F401
    EnergyCostTariffSourceSettings,
    EntsoeDayAheadTariffSourceSettings,
    TariffModuleSettings,
)
from cofy.modules.timeseries import TimeseriesModuleSettings, TimeseriesSourceSettings  # noqa: F401

from ..persitance.modules import ModulesPersistence

MODULE_SETTINGS_TYPE = ModuleSettings.union_type()

# polymorphic serialisation is not supported by fastapi, see https://github.com/fastapi/fastapi/discussions/15498
# we monkey patch it in by turning it on by default for all TypeAdapter.dump_json calls, but still allow it to be turned off if needed
original_dump_json = TypeAdapter.dump_json


def monkey_patched_dump_json(self: TypeAdapter, *args, polymorphic_serialization: bool = True, **kwargs):
    return original_dump_json(self, *args, polymorphic_serialization=polymorphic_serialization, **kwargs)


TypeAdapter.dump_json = monkey_patched_dump_json


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
        # return JSONResponse(content=[m.model_dump(polymorphic_serialization=True) for m in self.persistence.all(slug)])

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
