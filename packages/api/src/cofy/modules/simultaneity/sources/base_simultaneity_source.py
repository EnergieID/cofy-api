import asyncio
import datetime as dt
from abc import ABC, abstractmethod
from collections.abc import Sequence

import narwhals as nw

from cofy.modules.timeseries import CacheSettings, ISODuration, Timeseries

from ..source import NetVolumeSource, RatioSource


class BaseSimultaneitySource(RatioSource, ABC):
    def __init__(self, sources: Sequence[NetVolumeSource], cache: CacheSettings | None = None):
        """Consumption as a percentage of production per timestamp, over sources of net volumes.

        Args:
            sources: Sources of net volumes, positive for consumption and negative for production.
            cache: Cache what this source fetches, see `TimeseriesSource`.
        """
        super().__init__(cache=cache)
        if not sources:
            raise ValueError("At least one source must be provided")
        self.sources = sources

    @abstractmethod
    def volumes(self, results: Sequence[Timeseries]) -> nw.DataFrame:
        """The consumption and production to compare per timestamp, from the results of the sources in order."""

    async def _fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        results = await asyncio.gather(
            *(source.fetch_timeseries(start, end, resolution, **kwargs) for source in self.sources)
        )

        consumption = nw.col("consumption")
        production = nw.col("production")
        frame = (
            self.volumes(results)
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

        metadata: dict = {"unit": "%"}
        # the result is only as fresh as its least fresh input
        expires = [ts.metadata["expires"] for ts in results if "expires" in ts.metadata]
        if expires:
            metadata["expires"] = min(expires)
        return Timeseries(frame=frame, metadata=metadata)

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
