from src.shared.timeseries.module import TimeseriesModule


class ProductionModule(TimeseriesModule):
    type: str = "production"
    type_description: str = "Module providing production data as time series."
