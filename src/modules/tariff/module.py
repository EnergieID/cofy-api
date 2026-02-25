import datetime as dt
from typing import Annotated

from fastapi.params import Query
from pydantic import Field

from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.formats.csv import CSVFormat
from src.shared.timeseries.formats.json import (
    DefaultDataType,
    DefaultMetadataType,
    JSONFormat,
)
from src.shared.timeseries.module import TimeseriesModule
from src.shared.timeseries.source import TimeseriesSource


class TariffMetadata(DefaultMetadataType):
    unit: str


def floor_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Floor a datetime object to the nearest lower multiple of delta."""
    seconds = (dt_obj - dt.datetime.min.replace(tzinfo=dt_obj.tzinfo)).total_seconds()
    floored_seconds = seconds - (seconds % delta.total_seconds())
    return dt.datetime.min.replace(tzinfo=dt_obj.tzinfo) + dt.timedelta(seconds=floored_seconds)


class TariffModule(TimeseriesModule):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    def __init__(
        self,
        *,
        source: TimeseriesSource | None = None,
        api_key: str = "",
        country_code: str | None = None,
        formats: list[TimeseriesFormat] | None = None,
        supported_resolutions: list[str] | None = None,
        extra_args: dict | None = None,
        **kwargs,
    ):
        if formats is None:
            formats = [
                JSONFormat[DefaultDataType, TariffMetadata](DefaultDataType, TariffMetadata),
                CSVFormat(),
            ]
        if source is None:
            # use default source, with its own defaults for country_code and resolution
            source = EntsoeDayAheadTariffSource(
                api_key=api_key,
                country_code=country_code or "BE",
            )

            if country_code is None and (extra_args is None or "country_code" not in extra_args):
                extra_args = extra_args or {}
                extra_args["country_code"] = Annotated[
                    str,
                    Field(Query(default="BE", description="Country code for ENTSOE")),
                ]

        if supported_resolutions is None:
            supported_resolutions = ["PT15M"]
        super().__init__(
            source=source,
            formats=formats,
            supported_resolutions=supported_resolutions,
            extra_args=extra_args,
            **kwargs,
        )

    @property
    def default_args(self):
        return {
            "start": lambda: floor_datetime(dt.datetime.now(dt.UTC), dt.timedelta(minutes=15)),
            "end": lambda: None,
            "offset": 0,
            "limit": 288,
            "resolution": "PT15M",
        }
