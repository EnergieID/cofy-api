from abc import ABC, abstractmethod

from fastapi import Response
from fastapi.responses import JSONResponse

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin

from .model import Timeseries


class TimeseriesFormatSettings(BaseSettingsModel):
    type: str = "timeseries_format"


class TimeseriesFormat(FromSettingsMixin, ABC, settings=TimeseriesFormatSettings):
    @abstractmethod
    def format(self, timeseries: Timeseries) -> object:
        """Format the timeseries data into a Response object."""

    @property
    @abstractmethod
    def ReturnType(self) -> type:
        """Return the Response type for this format."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the format."""

    @property
    def responses(self) -> dict:
        """Return the OpenAPI response schema for this format."""
        return {
            200: {
                "model": self.ReturnType,
                "description": f"Timeseries data in {self.name} format",
            }
        }

    @property
    def response_class(self) -> type[Response]:
        """Return the response class for this format."""
        return JSONResponse
