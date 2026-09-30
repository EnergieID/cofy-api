import datetime as dt

import polars as pl

from cofy.modules.simultaneity import NetVolumeSource
from cofy.modules.timeseries import ISODuration, Timeseries

START = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
QUARTER = dt.timedelta(minutes=15)


class FixedSource(NetVolumeSource):
    """Returns the given values at consecutive quarter-hours from START."""

    def __init__(
        self,
        values: list[float],
        *,
        metadata: dict | None = None,
        resolutions: list[str] | None = None,
        max_age: dt.timedelta | None = None,
    ):
        super().__init__()
        self.values = values
        self.metadata = metadata or {}
        self.resolutions = resolutions or []
        self._max_age = max_age

    async def _fetch_timeseries(
        self, start: dt.datetime, end: dt.datetime, resolution: ISODuration, **kwargs
    ) -> Timeseries:
        data = {"timestamp": [START + i * QUARTER for i in range(len(self.values))], "value": self.values}
        frame = pl.DataFrame(data, schema={"timestamp": pl.Datetime(time_zone="UTC"), "value": pl.Float64})
        return Timeseries(frame=frame, metadata=dict(self.metadata))

    @property
    def supported_resolutions(self) -> list[str]:
        return self.resolutions

    @property
    def max_age(self) -> dt.timedelta | None:
        return self._max_age
