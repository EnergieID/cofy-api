import datetime as dt
from typing import Literal

from cofy.modules.timeseries import (
    ISODuration,
    NumericSource,
    NumericSourceSettings,
    Timeseries,
    TimeseriesSource,
    TimeseriesSourceSettings,
)


class DummyTimeseriesSourceSettings(TimeseriesSourceSettings):
    type: Literal["dummy_timeseries_source"] = "dummy_timeseries_source"


class DummyTimeseriesSource(TimeseriesSource, settings=DummyTimeseriesSourceSettings):
    async def _fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration = dt.timedelta(hours=1),
        **kwargs,
    ):
        import pandas as pd

        data = []

        i = 0
        while start + i * resolution < end:
            data.append({"timestamp": start + i * resolution, "value": i * 10.0})
            i += 1

        frame = pd.DataFrame(data)
        return Timeseries(metadata={"foo": "bar", **kwargs}, frame=frame)


class DummyNumericSourceSettings(NumericSourceSettings):
    type: Literal["dummy_numeric_source"] = "dummy_numeric_source"


class DummyNumericSource(DummyTimeseriesSource, NumericSource, settings=DummyNumericSourceSettings):
    """The dummy source, as a source of numeric values."""
