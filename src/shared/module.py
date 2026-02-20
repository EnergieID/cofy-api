from abc import ABC, abstractmethod
from typing import Any

from fastapi import APIRouter


class Module(APIRouter, ABC):
    type: str = "module"
    type_description: str = "Generic module"
    settings: dict

    def __init__(self, settings: dict, **kwargs):
        self.settings = settings
        default_router_kwargs = {
            "prefix": f"/{self.type}/{self.name}/{self.version}",
            "tags": [self.id],
        }
        super().__init__(**(default_router_kwargs | kwargs))  # ty: ignore[invalid-argument-type]
        self.init_routes()

    @abstractmethod
    def init_routes(self):
        """Initialize the routes of the module."""

    def add_api_route(
        self, path: str, endpoint: Any, *args, operation_id: str | None = None, **kwargs
    ):
        """Add an API route to the module."""
        if operation_id is None:
            operation_id = f"{self.id}:{endpoint.__name__}"
        else:
            operation_id = f"{self.id}:{operation_id}"

        super().add_api_route(
            path, endpoint, *args, operation_id=operation_id, **kwargs
        )

    @property
    def name(self) -> str:
        """The name of the module instance, e.g. "entsoe_tariff", "openweather", etc.
        Use it to differentiate between multiple instances/implementations of the same module type.
        """
        return self.settings.get("name", "default")

    @property
    def id(self) -> str:
        """The unique identifier of the module instance, e.g. "tariff:entsoe_tariff" """
        return f"{self.type}:{self.name}"

    @property
    def version(self) -> str:
        """The version of the module."""
        return "v1"

    @property
    def tag(self) -> dict[str, Any]:
        """The tag info of the implementation."""
        return {
            "name": self.id,
            "description": self.settings.get("description", self.type_description),
            "x-module-type": self.type,
            "x-version": self.version,
            "x-display-name": self.settings.get("display_name", self.name),
        }
