import datetime as dt
from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import Field

from cofy.api import BaseSettingsModel, FromSettingsMixin, Referable

from .cache import CacheSettings, TimeseriesCache
from .model import ISODuration, Timeseries


class TimeseriesSourceSettings(BaseSettingsModel):
    type: Literal["timeseries_source"] = "timeseries_source"
    cache: CacheSettings | None = Field(None, description="Cache what this source fetches, if set.")

    @classmethod
    def union_annotations(cls) -> tuple[Any, ...]:
        # Wherever a source of this family fits, a reference to a source resource holding one fits too.
        return (Referable("source", family=cls),)


class TimeseriesSource(FromSettingsMixin, ABC, settings=TimeseriesSourceSettings, abstract=True):
    """A source of any timeseries."""

    def __init__(self, cache: CacheSettings | None = None):
        """A source caching what it fetches if `cache` is given, for the source's own max_age unless it says otherwise."""
        self._cache = (
            TimeseriesCache(self._fetch_timeseries, cache, lambda: self.max_age) if cache is not None else None
        )

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        """Fetch timeseries data between start and end datetimes with the given resolution, from the cache if enabled."""
        if self._cache is not None:
            return await self._cache.fetch(start, end, resolution, **kwargs)
        return await self._fetch_timeseries(start, end, resolution, **kwargs)

    @abstractmethod
    async def _fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        """Fetch the timeseries data itself, uncached."""

    @property
    def cache(self) -> TimeseriesCache | None:
        """The cache this source serves from, if enabled."""
        return self._cache

    @property
    def supported_resolutions(self) -> list[str]:
        """Optionally specify supported resolutions for this source, e.g. ["PT15M", "P1D"]. If empty, all resolutions are supported."""
        return []

    @property
    def extra_args(self) -> dict:
        """Optionally specify extra keyword args that this source supports, e.g. {"country_code": str}. This can be used by the frontend to dynamically generate query forms."""
        return {}

    @property
    def max_age(self) -> dt.timedelta | None:
        """Optionally specify how long fetched data stays valid, used for caching. None means unknown."""
        return None


class NumericSourceSettings(TimeseriesSourceSettings):
    type: Literal["numeric_source"] = "numeric_source"


class NumericSource(TimeseriesSource, settings=NumericSourceSettings, abstract=True):
    """A source of numeric values."""
