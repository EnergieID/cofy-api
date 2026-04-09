import asyncio
import datetime as dt
from typing import Annotated

import pandas as pd
from energy_cost.tariff import MeterType, PowerDirection, Tariff
from fastapi import Query
from isodate import Duration

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource


class EnergyCostTariffSource(TimeseriesSource):
    def __init__(self, yaml_config: str, meter_type: MeterType | None = None, direction: PowerDirection | None = None):
        super().__init__()
        self.tariff = Tariff.from_yaml(yaml_config)
        self.meter_type = meter_type
        self.direction = direction

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration = dt.timedelta(minutes=15),
        meter_type: MeterType | None = None,
        direction: PowerDirection | None = None,
        **kwargs,
    ) -> Timeseries:
        if isinstance(resolution, Duration):
            raise ValueError(
                "Resolution only support time components, not years or months, as they cannot be converted to a fixed number of seconds."
            )
        meter_type = meter_type or self.meter_type
        direction = direction or self.direction
        if meter_type is None:
            raise ValueError("meter_type must be provided.")
        if direction is None:
            raise ValueError("direction must be provided.")
        series = await asyncio.to_thread(
            self.tariff.get_energy_cost,
            start=start,
            end=end,
            resolution=resolution,
            meter_type=meter_type,
            direction=direction,
        )
        if series is None:
            raise ValueError("No tariff data available for the given parameters.")
        df = series.rename(columns={"total": "value"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return Timeseries(frame=df, metadata={"unit": "EUR/MWh"})

    @property
    def supported_resolutions(self) -> list[str]:
        return ["PT5M", "PT15M", "PT1H", "P1D", "P7D"]

    @property
    def extra_args(self) -> dict:
        result = {}
        if self.meter_type is None:
            result["meter_type"] = Annotated[
                MeterType,
                Query(
                    default=MeterType.SINGLE_RATE,
                ),
            ]
        if self.direction is None:
            result["direction"] = Annotated[
                PowerDirection,
                Query(
                    default=PowerDirection.CONSUMPTION,
                ),
            ]

        return result
