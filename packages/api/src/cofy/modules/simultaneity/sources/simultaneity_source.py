import asyncio
import datetime as dt
from typing import TYPE_CHECKING, Literal

import narwhals as nw
from pydantic import Field

from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource, TimeseriesSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyTimeseriesSourceSettings = TimeseriesSourceSettings


class SimultaneitySourceSettings(TimeseriesSourceSettings):
    type: Literal["simultaneity"] = "simultaneity"
    # Unresolved until cofy.api.finalize() publishes the discriminated unions.
    sources: "list[AnyTimeseriesSourceSettings]" = Field(min_length=1)


class SimultaneitySource(TimeseriesSource, settings=SimultaneitySourceSettings):
    def __init__(self, sources: list[TimeseriesSource]):
        """Total consumption as a percentage of total production per timestamp, over sources of net volumes.

        Args:
            sources: Sources of net volumes, positive for consumption and negative for production.
        """
        if not sources:
            raise ValueError("At least one source must be provided")
        self.sources = sources

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        results = await asyncio.gather(
            *(source.fetch_timeseries(start, end, resolution, **kwargs) for source in self.sources)
        )

        frames = [ts.frame.select("timestamp", "value") for ts in results]

        consumption = nw.col("consumption")
        production = nw.col("production")
        frame = (
            nw.concat(frames)
            .group_by("timestamp")
            .agg(
                nw.col("value").clip(lower_bound=0).sum().alias("consumption"),
                (-nw.col("value").clip(upper_bound=0)).sum().alias("production"),
            )
            .with_columns(
                # no volume at all is neither surplus nor shortage, so report it as balanced
                value=nw.when((consumption == 0) & (production == 0))
                .then(nw.lit(100.0))
                .when(production == 0)
                .then(nw.lit(float("inf")))
                .otherwise(consumption / production * 100)
            )
            .select("timestamp", "value")
            .sort("timestamp")
        )

        result = Timeseries(frame=frame, metadata={"unit": "%"})
        # the result is only as fresh as its least fresh input
        expires = [ts.metadata["expires"] for ts in results if "expires" in ts.metadata]
        if expires:
            result.metadata["expires"] = min(expires)
        return result

    @property
    def supported_resolutions(self) -> list[str]:
        # an empty list means a source supports all resolutions, so it doesn't constrain the intersection
        constrained = [set(source.supported_resolutions) for source in self.sources if source.supported_resolutions]
        if not constrained:
            return []
        return list(set.intersection(*constrained))

    @property
    def max_age(self) -> dt.timedelta | None:
        # the result is only as fresh as its least fresh input, and unknown if any input is unknown
        max_ages = [source.max_age for source in self.sources]
        known = [max_age for max_age in max_ages if max_age is not None]
        if len(known) < len(max_ages):
            return None
        return min(known)
