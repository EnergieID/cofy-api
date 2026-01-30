import asyncio
import datetime as dt

import pandas as pd
from entsoe import EntsoePandasClient

from src.shared.timeseries.model import Timeseries
from src.shared.timeseries.source import TimeseriesSource


class EntsoeDayAheadTariffSource(TimeseriesSource):
    def __init__(self, country_code: str, api_key: str):
        super().__init__()
        if not country_code:
            raise ValueError("country_code must be provided")
        if not api_key:
            raise ValueError("api_key must be provided")

        self.country_code = country_code
        self.client = EntsoePandasClient(api_key=api_key)

    async def fetch_timeseries(
        self, start: dt.datetime, end: dt.datetime, **kwargs
    ) -> Timeseries:
        series = await asyncio.to_thread(
            self.client.query_day_ahead_prices,
            country_code=self.country_code,
            start=pd.Timestamp(start),
            end=pd.Timestamp(end),
        )
        df = (
            series.to_frame()
            .reset_index()
            .rename(columns={"index": "timestamp", 0: "value"})
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return Timeseries(frame=df, metadata={"unit": "EUR/MWh"})
