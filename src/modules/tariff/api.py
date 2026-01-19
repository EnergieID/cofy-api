from fastapi import APIRouter
import datetime as dt

from src.modules.tariff.model import TariffEntry
from src.modules.tariff.source import TariffSource


class TariffAPI:
    source: TariffSource
    router: APIRouter

    def __init__(self, source: TariffSource):
        self.source = source
        self.router = APIRouter()
        self.router.add_api_route("/v1", self.get_tariffs, methods=["GET"])

    def get_tariffs(self,
            start: dt.datetime,
            end: dt.datetime
        ) -> list[TariffEntry]:
        frame = self.source.fetch_tariffs(start, end)

        return frame.entries.to_dicts()