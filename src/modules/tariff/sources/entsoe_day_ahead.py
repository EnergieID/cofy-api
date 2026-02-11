import asyncio
import datetime as dt

import pandas as pd
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError

from src.shared.timeseries.model import Timeseries
from src.shared.timeseries.source import TimeseriesSource


class EntsoeDayAheadTariffSource(TimeseriesSource):
    def __init__(self, api_key: str, country_code: str | None = None):
        super().__init__()
        if not api_key:
            raise ValueError("api_key must be provided")

        self.country_code = country_code
        self.client = EntsoePandasClient(api_key=api_key)

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        country_code: str | None = None,
        **kwargs,
    ) -> Timeseries:
        try:
            series = await asyncio.to_thread(
                self.client.query_day_ahead_prices,
                country_code=country_code or self.country_code,
                start=pd.Timestamp(start),
                end=pd.Timestamp(end),
            )
        except NoMatchingDataError:
            series = pd.Series(dtype=float)
        df = (
            series.to_frame()
            .reset_index()
            .rename(columns={"index": "timestamp", 0: "value"})
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return Timeseries(frame=df, metadata={"unit": "EUR/MWh"})
