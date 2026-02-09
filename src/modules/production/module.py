from src.shared.timeseries.module import TimeseriesModule


class ProductionModule(TimeseriesModule):
    type: str = "production"
    type_description: str = "Module providing production data as time series."

    def __init__(self, settings: dict, **kwargs):
        super().__init__(settings, **kwargs)
