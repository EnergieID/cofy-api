from typing import Literal

from cofy.modules.timeseries import TimeseriesModule
from cofy.modules.timeseries.module import TimeseriesModuleSettings


class SimultaneityModuleSettings(TimeseriesModuleSettings):
    type: Literal["simultaneity"] = "simultaneity"


class SimultaneityModule(TimeseriesModule, settings=SimultaneityModuleSettings):
    type: str = "simultaneity"
    type_description: str = "Module providing the simultaneity of consumption and production as time series."
