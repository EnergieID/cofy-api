import datetime as dt
from typing import TYPE_CHECKING, Literal

import narwhals as nw
from pydantic import Field

from cofy.modules.timeseries import CacheSettings, ISODuration, NumericSource, NumericSourceSettings, Timeseries

from ..formats.directive import DIRECTIVE_STEPS
from ..source import DirectiveSeriesSource, DirectiveSeriesSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyNumericSourceSettings = NumericSourceSettings


class DirectiveSourceSettings(DirectiveSeriesSourceSettings):
    type: Literal["directive"] = "directive"
    # Unresolved until cofy.api.finalize() publishes the discriminated unions.
    source: "AnyNumericSourceSettings"
    boundaries: tuple[float, float, float, float]
    reverse: bool = Field(default=False)


class DirectiveSource(DirectiveSeriesSource, settings=DirectiveSourceSettings):
    def __init__(
        self,
        source: NumericSource,
        boundaries: tuple[float, float, float, float],
        reverse: bool = False,
        cache: CacheSettings | None = None,
    ):
        """A TimeseriesSource that maps numeric values to directive steps based on provided boundaries.

        Args:
            source: The underlying TimeseriesSource to fetch data from.
            boundaries: A tuple of four float values that define the thresholds for mapping numeric values to directive steps. The values should be in ascending order and correspond to the steps in DIRECTIVE_STEPS
            reverse: If True, the mapping of values to directive steps will be reversed (i.e., higher values will correspond to more negative steps).
            cache: Cache what this source fetches, see `TimeseriesSource`.
        """
        super().__init__(cache=cache)
        self.source = source
        self.boundaries = boundaries
        self.reverse = reverse

    async def _fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration,
        **kwargs,
    ) -> Timeseries:
        timeseries = await self.source.fetch_timeseries(start, end, resolution, **kwargs)

        steps = DIRECTIVE_STEPS if not self.reverse else list(reversed(DIRECTIVE_STEPS))

        expr = nw.lit(steps[0])
        for boundry, step in list(zip(self.boundaries, steps[1:], strict=True)):
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

    @property
    def max_age(self) -> dt.timedelta | None:
        return self.source.max_age
