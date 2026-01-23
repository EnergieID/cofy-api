import datetime as dt

from modules.tariff.model import TariffFrame
from modules.tariff.source import TariffSource


class DummySource(TariffSource):
    async def fetch_tariffs(self, start: dt.datetime, end: dt.datetime) -> TariffFrame:
        data = [
            {"timestamp": start + dt.timedelta(hours=i), "value": i * 10.0}
            for i in range(int((end - start).total_seconds() // 3600))
        ]
        return TariffFrame(unit="EUR/MWh", entries=data)
