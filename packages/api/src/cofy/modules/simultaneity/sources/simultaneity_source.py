from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

import narwhals as nw
from pydantic import Field

from cofy.modules.timeseries import Timeseries

from ..source import NetVolumeSourceSettings, RatioSourceSettings
from .base_simultaneity_source import BaseSimultaneitySource

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyNetVolumeSourceSettings = NetVolumeSourceSettings


class SimultaneitySourceSettings(RatioSourceSettings):
    type: Literal["simultaneity"] = "simultaneity"
    # Unresolved until cofy.api.finalize() publishes the discriminated unions.
    sources: "list[AnyNetVolumeSourceSettings]" = Field(min_length=1)


class SimultaneitySource(BaseSimultaneitySource, settings=SimultaneitySourceSettings):
    """Total consumption as a percentage of total production, each source consuming or producing by its sign."""

    def volumes(self, results: Sequence[Timeseries]) -> nw.DataFrame:
        return (
            nw.concat([ts.frame.select("timestamp", "value") for ts in results])
            .group_by("timestamp")
            .agg(
                nw.col("value").clip(lower_bound=0).sum().alias("consumption"),
                (-nw.col("value").clip(upper_bound=0)).sum().alias("production"),
            )
        )
