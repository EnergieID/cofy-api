from abc import ABC, abstractmethod
import datetime as dt

from src.modules.tariff.model import TariffFrame

class TariffSource(ABC):
    @abstractmethod
    async def fetch_tariffs(self, start: dt.datetime, end: dt.datetime) -> TariffFrame:
        pass