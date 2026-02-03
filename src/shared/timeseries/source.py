import datetime as dt
from abc import ABC, abstractmethod

from pydantic import BaseModel

from src.shared.timeseries.model import DefaultDataType, DefaultMetadataType, Timeseries


class TimeseriesSource[
    DataType: BaseModel = DefaultDataType,
    MetadataType: BaseModel = DefaultMetadataType,
](ABC):
    @abstractmethod
    async def fetch_timeseries(
        self, start: dt.datetime, end: dt.datetime, **kwargs
    ) -> Timeseries[DataType, MetadataType]:
        """Fetch timeseries data between start and end datetimes."""
