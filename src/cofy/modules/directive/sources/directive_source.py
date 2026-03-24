import datetime as dt

import narwhals as nw

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource

from ..formats.directive import DIRECTIVE_STEPS


class DirectiveSource(TimeseriesSource):
    def __init__(self, source: TimeseriesSource, boundries: tuple[float, float, float, float]):
        self.source = source
        self.boundries = boundries

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        timeseries = await self.source.fetch_timeseries(start, end, resolution, **kwargs)

        expr = nw.lit(DIRECTIVE_STEPS[0])
        for boundry, step in list(zip(self.boundries, DIRECTIVE_STEPS[1:], strict=True)):
            expr = nw.when(nw.col("value") > boundry).then(nw.lit(step)).otherwise(expr)

        timeseries.frame = timeseries.frame.with_columns(value=expr)
        timeseries.metadata["unit"] = "directive"
        return timeseries

    @property
    def supported_resolutions(self) -> list[str]:
        return self.source.supported_resolutions

    @property
    def extra_args(self) -> dict:
        return self.source.extra_args
