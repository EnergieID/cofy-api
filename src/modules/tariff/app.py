from fastapi import APIRouter

from src.modules.tariff.router import TariffRouter
from src.modules.tariff.source import TariffSource
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.module import Module


class TariffApp(Module):
    source: TariffSource
    _router: TariffRouter

    def __init__(self, settings: dict):
        super().__init__(settings)
        if "source" in settings:
            self.source = settings["source"]
        else:
            self.source = EntsoeDayAheadTariffSource(
                settings.get("country_code", "BE"),
                settings.get("api_key", ""),
            )
        self._router = TariffRouter(self.source)

    @property
    def router(self) -> APIRouter:
        return self._router

    @property
    def type(self) -> str:
        return "tariff"
