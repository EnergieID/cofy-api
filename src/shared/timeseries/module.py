import datetime as dt
from typing import Annotated

from fastapi import Depends, Query
from fastapi.exceptions import RequestValidationError
from pydantic import create_model

from src.shared.module import Module
from src.shared.timeseries.format import TimeseriesFormat
from src.shared.timeseries.formats.csv import CSVFormat
from src.shared.timeseries.formats.json import JSONFormat
from src.shared.timeseries.source import TimeseriesSource


class TimeseriesModule(Module):
    type: str = "timeseries"
    type_description: str = "Module providing timeseries data."
    source: TimeseriesSource
    formats: list[TimeseriesFormat]

    def __init__(self, settings: dict, **kwargs):
        self.formats = settings.get(
            "formats",
            [
                JSONFormat(),
                CSVFormat(),
            ],
        )
        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]

    def init_routes(self):
        super().init_routes()

        for format in self.formats:
            self.create_format_endpoint(format)

    @property
    def DynamicParameters(self):
        return create_model("DynamicParameters", **self.settings.get("extra_args", {}))

    def create_format_endpoint(self, format: TimeseriesFormat):
        params_default = Depends()

        async def get_timeseries(
            start: Annotated[
                dt.datetime,
                Query(
                    default_factory=self.merged_default_args["start"],
                    description="Start datetime in ISO8601 format",
                ),
            ],
            end: Annotated[
                dt.datetime | None,
                Query(
                    default_factory=self.merged_default_args["end"],
                    description="End datetime in ISO8601 format",
                ),
            ],
            offset: Annotated[
                int | None, Query(description="Offset in number of resolution steps")
            ] = self.merged_default_args["offset"],
            limit: Annotated[
                int | None, Query(description="Limit number of resolution steps")
            ] = self.merged_default_args["limit"],
            params: self.DynamicParameters = params_default,
        ):
            # validate inputs
            if limit is None and end is None:
                raise RequestValidationError(
                    "Either end datetime or limit must be provided."
                )
            if limit is None and end is not None and start >= end:
                raise RequestValidationError(
                    "Start datetime must be before end datetime."
                )
            # If no timezone is provided, assume UTC
            if start.tzinfo is None:
                start = start.replace(tzinfo=dt.UTC)
            if end is not None and end.tzinfo is None:
                end = end.replace(tzinfo=dt.UTC)
            # calculate adjusted start and end based on offset and limit
            if offset is not None:
                start += offset * self.resolution
                if end is not None:
                    end += offset * self.resolution
            if limit is not None:
                end = start + limit * self.resolution

            if end is None:
                raise RequestValidationError(
                    "Either end datetime or limit must be provided."
                )

            # extract extra args
            extra_args = params.dict(exclude_unset=True)

            # fetch timeseries data
            timeseries = await self.source.fetch_timeseries(start, end, **extra_args)

            # add metadata
            timeseries.metadata["start"] = start
            timeseries.metadata["end"] = end
            timeseries.metadata["resolution"] = self.resolution
            timeseries.metadata["format"] = format.name

            # return in requested format
            return format.format(timeseries)

        self.add_api_route(
            f".{format.name}",
            get_timeseries,
            methods=["GET"],
            responses=format.responses,
            response_class=format.response_class,
        )

    @property
    def default_args(self):
        return {
            "start": lambda: dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            "end": lambda: dt.datetime.now(dt.UTC),
            "offset": 0,
            "limit": None,
            "format": "json",
        }

    @property
    def merged_default_args(self):
        return self.default_args() | self.settings.get("default_args", {})

    @property
    def resolution(self) -> dt.timedelta:
        return self.settings.get("resolution", dt.timedelta(hours=1))
