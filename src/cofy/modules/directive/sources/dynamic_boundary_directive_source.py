import asyncio
import datetime as dt

import narwhals as nw

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource

from ..formats.directive import DIRECTIVE_STEPS

BOUNDARY_COLUMNS = ("b0", "b1", "b2", "b3")


class DynamicBoundaryDirectiveSource(TimeseriesSource):
    def __init__(
        self,
        signal_source: TimeseriesSource,
        boundary_source: TimeseriesSource,
        reverse: bool = False,
    ):
        """A TimeseriesSource that maps numeric values to directive steps using per-timestamp dynamic boundaries.

        Args:
            signal_source: The underlying TimeseriesSource providing the numeric signal values.
            boundary_source: A TimeseriesSource whose dataframe contains a 'timestamp' column and
                four boundary columns ('b0', 'b1', 'b2', 'b3') in ascending order, defining the
                thresholds between directive steps at each timestamp.
            reverse: If True, the mapping of values to directive steps will be reversed (i.e.,
                higher values will correspond to more negative steps).
        """
        self.signal_source = signal_source
        self.boundary_source = boundary_source
        self.reverse = reverse

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        signal_ts, boundary_ts = await asyncio.gather(
            self.signal_source.fetch_timeseries(start, end, resolution, **kwargs),
            self.boundary_source.fetch_timeseries(start, end, resolution, **kwargs),
        )

        combined = signal_ts.frame.join(boundary_ts.frame, on="timestamp", how="inner")

        steps = DIRECTIVE_STEPS if not self.reverse else list(reversed(DIRECTIVE_STEPS))

        expr = nw.lit(steps[0])
        for col_name, step in zip(BOUNDARY_COLUMNS, steps[1:], strict=True):
            expr = nw.when(nw.col("value") > nw.col(col_name)).then(nw.lit(step)).otherwise(expr)

        combined = combined.with_columns(value=expr).select(["timestamp", "value"])

        result = Timeseries(frame=combined, metadata=signal_ts.metadata)
        result.metadata["unit"] = "directive"
        return result

    @property
    def supported_resolutions(self) -> list[str]:
        # The supported resolutions are the intersection of the signal source and boundary source resolutions
        # if one returns an empty list, it means it supports all resolutions, so we can ignore it in the intersection
        signal_resolutions = set(self.signal_source.supported_resolutions)
        boundary_resolutions = set(self.boundary_source.supported_resolutions)
        if not signal_resolutions:
            return list(boundary_resolutions)
        if not boundary_resolutions:
            return list(signal_resolutions)
        return list(signal_resolutions & boundary_resolutions)

    @property
    def extra_args(self) -> dict:
        # The extra args are the union of the signal source and boundary source extra args, with signal source taking precedence in case of conflicts
        return {**self.boundary_source.extra_args, **self.signal_source.extra_args}
