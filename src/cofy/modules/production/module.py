from cofy.modules.timeseries import TimeseriesModule


class ProductionModule(TimeseriesModule):
    type: str = "production"
    type_description: str = "Module providing production data as time series."
