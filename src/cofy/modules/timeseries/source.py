import datetime as dt
from abc import ABC, abstractmethod

from cofy.modules.timeseries.model import Timeseries


class TimeseriesSource(ABC):
    @abstractmethod
    async def fetch_timeseries(self, start: dt.datetime, end: dt.datetime, **kwargs) -> Timeseries:
        """Fetch timeseries data between start and end datetimes."""
