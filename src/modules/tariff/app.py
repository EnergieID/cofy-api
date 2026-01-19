from src.shared.module import Module
from src.modules.tariff.source import TariffSource
from src.modules.tariff.api import TariffAPI
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

class TariffApp(Module):
    source: TariffSource
    api: TariffAPI

    def __init__(self, settings: dict):
        super().__init__(settings)
        self.source = settings.get("source", EntsoeDayAheadTariffSource(settings.get("country_code", "DE"), settings.get("api_key", "")))
        self.api = TariffAPI(self.source)

    def get_router(self):
        return self.api.router