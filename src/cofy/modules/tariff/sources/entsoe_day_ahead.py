import asyncio
import datetime as dt
from typing import Annotated

import pandas as pd
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError
from fastapi.params import Query
from pydantic import Field

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource


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
        resolution: ISODuration = dt.timedelta(minutes=15),
        country_code: str | None = None,
        **kwargs,
    ) -> Timeseries:
        if resolution != dt.timedelta(minutes=15):
            raise ValueError("Only 15-minute resolution is supported for EntsoeDayAheadTariffSource")

        country_code = country_code or self.country_code
        if country_code is None:
            raise ValueError("country_code must be provided")

        try:
            series = await asyncio.to_thread(
                self.client.query_day_ahead_prices,
                country_code=country_code,
                start=pd.Timestamp(start),
                end=pd.Timestamp(end),
            )
            # older dates may return hourly data, so we need to resample to 15-minute intervals
            series = series.resample("15min").ffill()

        except NoMatchingDataError:
            series = pd.Series(dtype=float)
        df = series.to_frame().reset_index().rename(columns={"index": "timestamp", 0: "value"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return Timeseries(frame=df, metadata={"unit": "EUR/MWh"})

    @property
    def supported_resolutions(self) -> list[str]:
        return ["PT15M"]

    @property
    def extra_args(self) -> dict:
        if self.country_code is not None:
            return {}

        return {
            "country_code": Annotated[
                str,
                Field(Query(default="BE", description="Country code for ENTSOE")),
            ]
        }
