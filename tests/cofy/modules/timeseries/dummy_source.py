import datetime as dt

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource, TimeseriesSourceSettings


class DummyTimeseriesSourceSettings(TimeseriesSourceSettings):
    type: str = "dummy_timeseries_source"


class DummyTimeseriesSource(TimeseriesSource, settings=DummyTimeseriesSourceSettings):
    async def fetch_timeseries(
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
