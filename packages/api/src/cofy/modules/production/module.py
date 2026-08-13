from cofy.modules.timeseries import TimeseriesModule
from cofy.modules.timeseries.module import TimeseriesModuleSettings


class ProductionModuleSettings(TimeseriesModuleSettings):
    type: str = "production"


class ProductionModule(TimeseriesModule, settings=ProductionModuleSettings):
    type: str = "production"
    type_description: str = "Module providing production data as time series."
