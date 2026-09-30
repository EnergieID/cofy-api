from typing import TYPE_CHECKING, Literal

from cofy.modules.timeseries import TimeseriesModule
from cofy.modules.timeseries.module import TimeseriesModuleSettings

from .source import RatioSource, RatioSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyRatioSourceSettings = RatioSourceSettings


class SimultaneityModuleSettings(TimeseriesModuleSettings):
    type: Literal["simultaneity"] = "simultaneity"
    source: "AnyRatioSourceSettings"


class SimultaneityModule(TimeseriesModule[RatioSource], settings=SimultaneityModuleSettings):
    type: str = "simultaneity"
    type_description: str = "Module providing the simultaneity of consumption and production as time series."
