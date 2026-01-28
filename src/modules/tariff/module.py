import datetime as dt

from src.modules.tariff.model import TariffEntry
from src.modules.tariff.source import TariffSource
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from src.shared.module import Module


class TariffModule(Module):
    source: TariffSource

    def __init__(self, settings: dict, **kwargs):
        super().__init__(settings, **kwargs)
        if "source" in settings:
            self.source = settings["source"]
        else:
            self.source = EntsoeDayAheadTariffSource(
                settings.get("country_code", "BE"),
                settings.get("api_key", ""),
            )

    @property
    def type(self) -> str:
        return "tariff"

    def init_routes(self):
        super().init_routes()
        self.add_api_route("/", self.get_tariffs, methods=["GET"])

    async def get_tariffs(
        self,
        start: dt.datetime,
        end: dt.datetime,
    ) -> list[TariffEntry]:
        frame = await self.source.fetch_tariffs(start, end)
        return [TariffEntry(**row) for row in frame.entries.iter_rows(named=True)]
