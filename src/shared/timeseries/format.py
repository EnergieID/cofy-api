from abc import ABC, abstractmethod

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
