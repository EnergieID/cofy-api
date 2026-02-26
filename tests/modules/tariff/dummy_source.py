import datetime as dt

import pandas as pd

from cofy.modules.timeseries.model import Timeseries
from cofy.modules.timeseries.source import TimeseriesSource


class DummySource(TimeseriesSource):
    async def fetch_timeseries(self, start: dt.datetime, end: dt.datetime, **kwargs) -> Timeseries:
        data = [
            {"timestamp": start + dt.timedelta(hours=i), "value": i * 10.0}
            for i in range(int((end - start).total_seconds() // 3600))
        ]
        return Timeseries(metadata={"unit": "EUR/MWh"}, frame=pd.DataFrame(data))
