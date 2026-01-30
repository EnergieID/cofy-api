import datetime as dt
from collections.abc import Callable

from fastapi import Response
from fastapi.responses import JSONResponse

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
        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]

    def init_routes(self):
        super().init_routes()
        self.add_api_route("/", self.get_timeseries, methods=["GET"])

    def default_args(self):
        return {
            "start": lambda: dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            "end": lambda: dt.datetime.now(dt.UTC),
            "offset": 0,
            "limit": None,
            "format": "json",
        } | self.settings.get("default_args", {})

    @property
    def resolution(self) -> dt.timedelta:
        return self.settings.get("resolution", dt.timedelta(hours=1))

    async def get_timeseries(
        self,
        start: dt.datetime | None = None,
        end: dt.datetime | None = None,
        offset: int | None = None,
        limit: int | None = None,
        format: str | None = None,
    ):
        # apply defaults if None
        defaults = self.default_args()
        start = start or defaults["start"]()
        end = end or defaults["end"]()
        offset = offset or defaults["offset"]
        limit = limit or defaults["limit"]
        format = format or defaults["format"]

        # validate inputs
        if start >= end and limit is None:
            raise ValueError("Start datetime must be before end datetime.")
        if format not in self.formats:
            raise ValueError(f"Unsupported format: {format}")

        # calculate adjusted start and end based on offset and limit
        if offset is not None:
            start += offset * self.resolution
            end += offset * self.resolution
        if limit is not None:
            end = start + limit * self.resolution

        # fetch timeseries data
        timeseries = await self.source.fetch_timeseries(start, end)

        # return in requested format
        return self.formats[format](timeseries)
