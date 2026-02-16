from abc import ABC, abstractmethod
from typing import Any

from fastapi import APIRouter
from fastapi.openapi.utils import get_openapi

from src.cofy.docs_router import DocsRouter


class Module(APIRouter, ABC):
    type: str = "module"
    type_description: str = "Generic module"
    settings: dict

    def __init__(self, settings: dict, **kwargs):
        self.settings = settings
        default_router_kwargs = {
            "prefix": f"/{self.type}/{self.name}/{self.version}",
            "tags": [self.type_tag["name"], self.tag["name"]],
        }
        super().__init__(**(default_router_kwargs | kwargs))  # ty: ignore[invalid-argument-type]
        self.init_routes()
        self.include_router(DocsRouter(self.openapi))

    def openapi(self):
        return get_openapi(
            title=f"{self.type}:{self.name} API",
            description=self.tag["description"],
            version=self.version,
            routes=self.routes,
            tags=[self.type_tag, self.tag],
        )

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
    def type_tag(self) -> dict[str, Any]:
        """The tag info of the module type."""
        return {
            "name": self.type,
            "description": self.type_description,
        }

    @property
    def tag(self) -> dict[str, Any]:
        """The tag info of the implementation."""
        return {
            "name": f"{self.type}:{self.name}",
            "description": self.settings.get("description", self.type_description),
            "x-version": self.version,
        }
