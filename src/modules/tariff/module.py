import datetime as dt

from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.timeseries.formats.csv import CSVFormat
from src.shared.timeseries.formats.json import (
    DefaultDataType,
    DefaultMetadataType,
    JSONFormat,
)
from src.shared.timeseries.module import TimeseriesModule


class TariffMetadata(DefaultMetadataType):
    unit: str


def floor_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Floor a datetime object to the nearest lower multiple of delta."""
    seconds = (dt_obj - dt.datetime.min.replace(tzinfo=dt_obj.tzinfo)).total_seconds()
    floored_seconds = seconds - (seconds % delta.total_seconds())
    return dt.datetime.min.replace(tzinfo=dt_obj.tzinfo) + dt.timedelta(
        seconds=floored_seconds
    )


class TariffModule(TimeseriesModule):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    def __init__(self, settings: dict, **kwargs):
        settings["formats"] = settings.get(
            "formats",
            [
                JSONFormat[DefaultDataType, TariffMetadata](
                    DefaultDataType, TariffMetadata
                ),
                CSVFormat(),
            ],
        )
        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]
        else:
            self.source = EntsoeDayAheadTariffSource(
                settings.get("country_code", "BE"),
                settings.get("api_key", ""),
            )

    def default_args(self):
        return {
            "start": lambda: floor_datetime(dt.datetime.now(dt.UTC), self.resolution),
            "end": lambda: None,
            "offset": 0,
            "limit": 288,
            "format": "kiwatt",
        }

    @property
    def resolution(self) -> dt.timedelta:
        return self.settings.get("resolution", dt.timedelta(minutes=15))
