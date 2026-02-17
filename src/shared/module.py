from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from sqlalchemy.sql.schema import MetaData


class Module(APIRouter, ABC):
    type: str = "module"
    type_description: str = "Generic module"
    settings: dict
    uses_database: bool = False
    migration_locations: list[str] = []
    target_metadata: MetaData | None = None

    def __init__(self, settings: dict, **kwargs):
        self.settings = settings
        default_router_kwargs = {
            "prefix": f"/{self.type}/{self.name}/{self.version}",
            "tags": [self.tag["name"]],
        }
        super().__init__(**(default_router_kwargs | kwargs))  # ty: ignore[invalid-argument-type]
        self.init_routes()

    @abstractmethod
    def init_routes(self):
        """Initialize the routes of the module."""

    @property
    def name(self) -> str:
        """The name of the module instance, e.g. "entsoe_tariff", "openweather", etc.
        Use it to differentiate between multiple instances/implementations of the same module type.
        """
        return self.settings.get("name", "default")

    @property
    def version(self) -> str:
        """The version of the module."""
        return "v1"

    @property
    def tag(self) -> dict[str, Any]:
        """The tag info of the implementation."""
        return {
            "name": f"{self.type}:{self.name}",
            "description": self.settings.get("description", self.type_description),
            "x-module-type": self.type,
            "x-version": self.version,
            "x-display-name": self.settings.get("display_name", self.name),
        }

    @property
    def resolved_migration_locations(self) -> list[str]:
        """Resolved absolute migration locations for this module."""
        return [
            str(Path(location).resolve())
            for location in self.migration_locations
            if location
        ]
