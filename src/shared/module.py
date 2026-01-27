from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

    from src.cofy.cofy_api import CofyApi

from abc import ABC, abstractmethod


class Module(ABC):
    cofy: CofyApi
    settings: dict

    def __init__(self, settings: dict):
        self.settings = settings

    @property
    @abstractmethod
    def router(self) -> APIRouter:
        """:return: A fastAPI router, that exposes the module's API endpoints.
        :rtype: APIRouter
        """

    @property
    @abstractmethod
    def type(self) -> str:
        """Describes the type of the module, e.g. "tariff", "weather", "storage", etc.
        Should be unique across all module types and defines the API and data model of the module.

        :rtype: str
        """

    @property
    def name(self) -> str:
        """The name of the module instance, e.g. "entsoe_tariff", "openweather", etc.
        Use it to differentiate between multiple instances/implementations of the same module type.

        :rtype: str
        """
        return self.settings.get("name", "default")

    @property
    def metadata(self) -> dict:
        """Metadata about the module instance.
        E.g. the unit of measurement, the data source, the update frequency, etc.

        :rtype: dict
        """
        return {}
