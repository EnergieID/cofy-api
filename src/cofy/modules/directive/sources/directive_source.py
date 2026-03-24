import datetime as dt

import narwhals as nw

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource

from ..formats.directive import DIRECTIVE_STEPS


class DirectiveSource(TimeseriesSource):
    def __init__(self, source: TimeseriesSource, boundries: tuple[float, float, float, float], reverse: bool = False):
        """A TimeseriesSource that maps numeric values to directive steps based on provided boundaries.

        Args:
            source: The underlying TimeseriesSource to fetch data from.
            boundries: A tuple of four float values that define the thresholds for mapping numeric values to directive steps. The values should be in ascending order and correspond to the steps in DIRECTIVE_STEPS
            reverse: If True, the mapping of values to directive steps will be reversed (i.e., higher values will correspond to more negative steps).
        """
        self.source = source
        self.boundries = boundries
        self.reverse = reverse

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        timeseries = await self.source.fetch_timeseries(start, end, resolution, **kwargs)

        steps = DIRECTIVE_STEPS if not self.reverse else list(reversed(DIRECTIVE_STEPS))

        expr = nw.lit(steps[0])
        for boundry, step in list(zip(self.boundries, steps[1:], strict=True)):
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
