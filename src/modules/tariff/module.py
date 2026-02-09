import datetime as dt
from typing import Annotated

from fastapi.params import Query
from pydantic import Field

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

        if "source" not in settings:
            # use default source, with its own defaults for country_code and resolution

            settings["source"] = EntsoeDayAheadTariffSource(
                settings.get("api_key", ""),
                settings.get("country_code", "BE"),
            )

            if "country_code" not in settings and (
                "extra_args" not in settings
                or "country_code" not in settings["extra_args"]
            ):
                settings["extra_args"] = settings.get("extra_args", {})
                settings["extra_args"]["country_code"] = Annotated[
                    str,
                    Field(Query(default="BE", description="Country code for ENTSOE")),
                ]

        if "supported_resolutions" not in settings:
            settings["supported_resolutions"] = [dt.timedelta(minutes=15)]
        super().__init__(settings, **kwargs)

    @property
    def default_args(self):
        return {
            "start": lambda: floor_datetime(
                dt.datetime.now(dt.UTC), dt.timedelta(minutes=15)
            ),
            "end": lambda: None,
            "offset": 0,
            "limit": 288,
            "resolution": dt.timedelta(minutes=15),
        }
