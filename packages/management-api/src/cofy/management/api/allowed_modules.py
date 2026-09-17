"""The module types a community is allowed to configure, with their JSON Schemas.

This is the frontend's entry point for building any module UI, and the single source of truth
for which types may be stored - `ModulesRouter` checks writes against the same list.

It exists as a dedicated endpoint rather than leaving clients to mine `/openapi.json`, because
generating the schema here sidesteps FastAPI's `-Input`/`-Output` split (`mode="validation"`
names the one that governs writes) and keeps every `$ref` local to the schema it appears in.
"""

from __future__ import annotations

from typing import Annotated, Any

from cofy.api.module import ModuleSettings
from cofy.modules.discovery import discover_all_types
from fastapi import APIRouter, Path
from pydantic import BaseModel, ConfigDict, Field

# Import every installed module/source/format type, so the registry is complete.
discover_all_types()


def allowed_module_types(slug: str) -> dict[str, type[ModuleSettings]]:
    """Module types *slug* may configure, keyed by type tag.

    Every installed type for now; per-community allow-lists are expected to be applied here,
    which is why callers pass a slug they do not yet need.
    """
    return ModuleSettings.registry()


class AllowedModule(BaseModel):
    """One module type a community may configure."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="Machine name, and the discriminator value in a module payload.")
    description: str = Field(description="What the module type does, from the module class.")
    json_schema: dict[str, Any] = Field(
        alias="schema",
        description="Self-contained JSON Schema for a full module settings payload of this type.",
    )


class AllowedModulesRouter:
    def __init__(self):
        self.router = APIRouter(prefix="/management/communities/{slug}/allowed-modules", tags=["Allowed modules"])
        self.router.add_api_route("", self.all, methods=["GET"])

    def all(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> list[AllowedModule]:
        """List the module types this community may configure."""
        return [
            AllowedModule(
                type=type_name,
                description=settings._model.type_description,
                schema=settings.model_json_schema(mode="validation"),
            )
            for type_name, settings in sorted(allowed_module_types(slug).items())
        ]
