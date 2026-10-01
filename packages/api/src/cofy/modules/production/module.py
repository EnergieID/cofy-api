from typing import TYPE_CHECKING, Literal

from cofy.modules.timeseries import TimeseriesModule
from cofy.modules.timeseries.module import TimeseriesModuleSettings

from .source import ProductionSource, ProductionSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyProductionSourceSettings = ProductionSourceSettings


class ProductionModuleSettings(TimeseriesModuleSettings):
    type: Literal["production"] = "production"
    source: "AnyProductionSourceSettings"


class ProductionModule(TimeseriesModule[ProductionSource], settings=ProductionModuleSettings):
    type: str = "production"
    type_description: str = "Module providing production data as time series."
