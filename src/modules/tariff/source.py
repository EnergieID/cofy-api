import datetime as dt
from abc import ABC, abstractmethod

from src.modules.tariff.model import TariffFrame


class TariffSource(ABC):
    @abstractmethod
    async def fetch_tariffs(self, start: dt.datetime, end: dt.datetime) -> TariffFrame:
        pass
