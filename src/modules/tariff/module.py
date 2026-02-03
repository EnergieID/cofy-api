import datetime as dt

from src.modules.tariff.formats.kiwatt import KiwattFormat
from src.modules.tariff.model import TariffMetadata
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.timeseries.formats.json import JSONFormat
from src.shared.timeseries.model import DefaultDataType
from src.shared.timeseries.module import TimeseriesModule


def floor_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Floor a datetime object to the nearest lower multiple of delta."""
    seconds = (dt_obj - dt.datetime.min.replace(tzinfo=dt_obj.tzinfo)).total_seconds()
    floored_seconds = seconds - (seconds % delta.total_seconds())
    return dt.datetime.min.replace(tzinfo=dt_obj.tzinfo) + dt.timedelta(
        seconds=floored_seconds
    )


class TariffModule(TimeseriesModule[DefaultDataType, TariffMetadata]):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    def __init__(self, settings: dict, **kwargs):
        settings["formats"] = [
            KiwattFormat(),
            JSONFormat[DefaultDataType, TariffMetadata](
                DefaultDataType, TariffMetadata
            ),
        ] + settings.get("formats", [])
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
