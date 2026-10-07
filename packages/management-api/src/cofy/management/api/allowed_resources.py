"""The resource kinds a community is allowed to configure, with their JSON Schemas.

The counterpart of `allowed_modules` for resources: the frontend's entry point for building a
resource UI, and the list `ResourcesRouter` checks writes against.
"""

from __future__ import annotations

from typing import Annotated, Any

from cofy.api import ResourceSettings
from cofy.modules.discovery import discover_all_types
from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field

from ..auth.access import Subject
from ..policies.policy import Policy, PolicyRouter

# Import every installed module/source/format type, so the registry is complete.
discover_all_types()


def allowed_resource_types(slug: str) -> dict[str, type[ResourceSettings]]:
    """Resource kinds *slug* may configure, keyed by type tag.

    Every installed kind for now; per-community allow-lists are expected to be applied here.
    """
    return ResourceSettings.registry()


class AllowedResource(BaseModel):
    """One resource kind a community may configure."""

    model_config = ConfigDict(populate_by_name=True)

    type: str = Field(description="Machine name, and the discriminator value in a resource payload.")
    description: str = Field(description="What a resource of this kind holds.")
    json_schema: dict[str, Any] = Field(
        alias="schema",
        description="Self-contained JSON Schema for a full resource payload of this kind.",
    )


class AllowedResourcesRouter:
    def __init__(self):
        self.router = PolicyRouter(
            subject=Subject.allowed_resources,
            prefix="/management/communities/{slug}/allowed-resources",
            tags=["Allowed resources"],
        )
        self.router.add_api_route("", self.all, methods=["GET"], rule=Policy.all)

    def all(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> list[AllowedResource]:
        """List the resource kinds this community may configure."""
        return [
            AllowedResource(
                type=type_name,
                description=(settings._model.__doc__ or "").strip(),
                schema=settings.model_json_schema(mode="validation"),
            )
            for type_name, settings in sorted(allowed_resource_types(slug).items())
        ]
