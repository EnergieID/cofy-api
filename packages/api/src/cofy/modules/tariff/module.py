import datetime as dt
from typing import Literal

from cofy.modules.timeseries import (
    TimeseriesModule,
    TimeseriesModuleSettings,
    floor_datetime,
)


class TariffModuleSettings(TimeseriesModuleSettings):
    type: Literal["tariff"] = "tariff"


class TariffModule(TimeseriesModule, settings=TariffModuleSettings):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    @property
    def default_args(self):
        return {
            "start": lambda: floor_datetime(dt.datetime.now(dt.UTC), dt.timedelta(minutes=15)),
            "end": lambda: None,
            "offset": 0,
            "limit": 288,
            "resolution": "PT15M",
        }
