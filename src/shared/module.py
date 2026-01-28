from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from abc import ABC, abstractmethod

from fastapi import APIRouter


class Module(APIRouter, ABC):
    settings: dict

    def __init__(self, settings: dict, **kwargs):
        self.settings = settings
        default_router_kwargs = {
            "prefix": f"/{self.type}/{self.name}/{self.version}",
            "tags": [self.type, f"{self.type}:{self.name}"],
        }
        super().__init__(**(default_router_kwargs | kwargs))  # ty: ignore[invalid-argument-type]
        self.init_routes()

    @property
    @abstractmethod
    def type(self) -> str:
        """Describes the type of the module, e.g. "tariff", "weather", "storage", etc.
        Should be unique across all module types and defines the API and data model of the module.

        :rtype: str
        """

    @abstractmethod
    def init_routes(self):
        """Initialize the routes of the module."""

    @property
    def name(self) -> str:
        """The name of the module instance, e.g. "entsoe_tariff", "openweather", etc.
        Use it to differentiate between multiple instances/implementations of the same module type.

        :rtype: str
        """
        return self.settings.get("name", "default")

    @property
    def version(self) -> str:
        """The version of the module.
        :rtype: str
        """
        return "v1"
