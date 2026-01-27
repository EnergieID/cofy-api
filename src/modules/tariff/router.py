import datetime as dt

from fastapi import APIRouter

from src.modules.tariff.model import TariffEntry
from src.modules.tariff.source import TariffSource


class TariffRouter(APIRouter):
    source: TariffSource

    def __init__(self, source: TariffSource):
        self.source = source
        super().__init__(prefix="/v0")
        self.add_api_route("/", self.get_tariffs, methods=["GET"])

    async def get_tariffs(
        self,
        start: dt.datetime,
        end: dt.datetime,
    ) -> list[TariffEntry]:
        frame = await self.source.fetch_tariffs(start, end)
        return [TariffEntry(**row) for row in frame.entries.iter_rows(named=True)]
