from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.timeseries.module import TimeseriesModule


class TariffModule(TimeseriesModule):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    def __init__(self, settings: dict, **kwargs):
        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]
        else:
            self.source = EntsoeDayAheadTariffSource(
                settings.get("country_code", "BE"),
                settings.get("api_key", ""),
            )
