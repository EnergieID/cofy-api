import datetime as dt
from abc import ABC, abstractmethod

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin

from .model import ISODuration, Timeseries


class TimeseriesSourceSettings(BaseSettingsModel):
    type: str = "timeseries_source"


class TimeseriesSource(FromSettingsMixin, ABC, settings=TimeseriesSourceSettings):
    @abstractmethod
    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        """Fetch timeseries data between start and end datetimes with the given resolution."""

    @property
    def supported_resolutions(self) -> list[str]:
        """Optionally specify supported resolutions for this source, e.g. ["PT15M", "P1D"]. If empty, all resolutions are supported."""
        return []

    @property
    def extra_args(self) -> dict:
        """Optionally specify extra keyword args that this source supports, e.g. {"country_code": str}. This can be used by the frontend to dynamically generate query forms."""
        return {}
