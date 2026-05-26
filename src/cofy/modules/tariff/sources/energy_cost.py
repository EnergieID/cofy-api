import asyncio
import datetime as dt
from typing import Annotated

import pandas as pd
from energy_cost import CostGroup, Tariff
from fastapi import Query
from isodate import Duration

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource


class EnergyCostTariffSource(TimeseriesSource):
    def __init__(self, yaml_config: str, cost_group: CostGroup | None = None):
        super().__init__()
        self.tariff = Tariff.from_yaml(yaml_config)
        self.cost_group = cost_group

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration = dt.timedelta(minutes=15),
        cost_group: CostGroup | None = None,
        **kwargs,
    ) -> Timeseries:
        if isinstance(resolution, Duration):
            raise ValueError(
                "Resolution only support time components, not years or months, as they cannot be converted to a fixed number of seconds."
            )
        cost_group = cost_group or self.cost_group
        if cost_group is None:
            raise ValueError("Cost group must be provided.")
        series = await asyncio.to_thread(
            self.tariff.get_values,
            start=start,
            end=end,
            output_resolution=resolution,
            cost_group=cost_group,
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
        if self.cost_group is None:
            result["cost_group"] = Annotated[
                CostGroup,
                Query(
                    default=CostGroup.CONSUMPTION,
                ),
            ]

        return result
