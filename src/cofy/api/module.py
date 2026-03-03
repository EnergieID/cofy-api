from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from fastapi import APIRouter


class Module(APIRouter, ABC):
    type: str = "module"
    type_description: str = "Generic module"

    def __init__(
        self,
        *,
        name: str = "default",
        description: str | None = None,
        display_name: str | None = None,
        prefix: str | None = None,
        tags: list[str | Enum] | None = None,
        **kwargs,
    ):
        self._name = name
        self._description = description
        self._display_name = display_name
        super().__init__(
            prefix=prefix if prefix is not None else f"/{self.type}/{self.name}/{self.version}",
            tags=tags if tags is not None else [self.id],
            **kwargs,
        )
        self.init_routes()

    @abstractmethod
    def init_routes(self):
        """Initialize the routes of the module."""

    def add_api_route(self, path: str, endpoint: Any, *args, operation_id: str | None = None, **kwargs):
        """Add an API route to the module."""
        operation_id = f"{self.id}:{operation_id or endpoint.__name__}"

        super().add_api_route(path, endpoint, *args, operation_id=operation_id, **kwargs)

    @property
    def name(self) -> str:
        """The name of the module instance, e.g. "entsoe_tariff", "openweather", etc.
        Use it to differentiate between multiple instances/implementations of the same module type.
        """
        return self._name

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
            "description": self._description if self._description is not None else self.type_description,
            "x-module-type": self.type,
            "x-version": self.version,
            "x-display-name": self._display_name if self._display_name is not None else self.name,
        }
