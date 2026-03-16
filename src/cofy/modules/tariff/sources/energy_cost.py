import asyncio
import datetime as dt

import pandas as pd
from energy_cost.tariff import MeterType, PowerDirection, Tariff
from isodate import Duration

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource


class EnergyCostTariffSource(TimeseriesSource):
    def __init__(self, yaml_config: str):
        super().__init__()
        self.tariff = Tariff.from_yaml(yaml_config)

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration = dt.timedelta(minutes=15),
        meter_type: MeterType = MeterType.SINGLE_RATE,
        direction: PowerDirection = PowerDirection.CONSUMPTION,
        **kwargs,
    ) -> Timeseries:
        if isinstance(resolution, Duration):
            raise ValueError(
                "Resolution only support time components, not years or months, as they cannot be converted to a fixed number of seconds."
            )
        series = await asyncio.to_thread(
            self.tariff.get_cost,
            start=start,
            end=end,
            resolution=resolution,
            meter_type=meter_type,
            direction=direction,
        )
        df = series.rename(columns={"total": "value"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        return Timeseries(frame=df, metadata={"unit": "EUR/MWh"})
