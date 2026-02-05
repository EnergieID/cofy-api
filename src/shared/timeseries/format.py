from abc import ABC, abstractmethod

from fastapi.responses import JSONResponse

from src.shared.timeseries.model import Timeseries


class TimeseriesFormat(ABC):
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
    def response_class(self) -> type:
        """Return the response class for this format."""
        return JSONResponse
