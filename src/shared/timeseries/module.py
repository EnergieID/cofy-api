import datetime as dt
from collections.abc import Callable
from enum import Enum
from typing import Annotated

from fastapi import Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

from src.shared.module import Module
from src.shared.timeseries.model import Timeseries
from src.shared.timeseries.source import TimeseriesSource


class TimeseriesModule(Module):
    type: str = "timeseries"
    type_description: str = "Module providing timeseries data."
    source: TimeseriesSource
    formats: dict[str, Callable[[Timeseries], Response]] = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.formats = {
            "json": cls.to_json_response,
            "csv": cls.to_csv_response,
        }

    @classmethod
    def to_json_response(cls, timeseries: Timeseries) -> Response:
        return JSONResponse(content=timeseries.to_dict())

    @classmethod
    def to_csv_response(cls, timeseries: Timeseries) -> Response:
        return Response(content=timeseries.to_csv(), media_type="text/csv")

    def __init__(self, settings: dict, **kwargs):
        if "formats" in settings:
            self.formats = settings["formats"] | self.formats

        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]

    def init_routes(self):
        super().init_routes()

        Format = Enum("Format", {k: k for k in self.formats})

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
            format: Annotated[
                Format, Query(description="Response format")
            ] = self.merged_default_args["format"],
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
            if format.value not in self.formats:
                raise RequestValidationError(f"Unsupported format: {format}")
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

            # fetch timeseries data
            timeseries = await self.source.fetch_timeseries(start, end)

            timeseries.metadata.update(
                {
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                    "format": format.value,
                    "resolution": TypeAdapter(dt.timedelta).dump_python(
                        self.resolution, mode="json"
                    ),
                }
            )

            # return in requested format
            return self.formats[format.value](timeseries)

        self.get_timeseries = get_timeseries
        self.add_api_route("/", self.get_timeseries, methods=["GET"])

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
