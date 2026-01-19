import narwhals
from src.modules.tariff.source import TariffSource
from src.modules.tariff.model import TariffFrame
from entsoe import EntsoePandasClient
import pandas as pd
import datetime as dt

class EntsoeDayAheadTariffSource(TariffSource):

    def __init__(self, country_code: str, api_key: str):
        super().__init__()
        self.country_code = country_code
        self.api_key = api_key
        self.client = EntsoePandasClient(api_key=api_key)

    async def fetch_tariffs(self, start: dt.datetime, end: dt.datetime) -> TariffFrame:
        pandas_frame: pd.DataFrame = self.client.query_day_ahead_prices(
            country_code=self.country_code
        )
        return TariffFrame(
            unit="EUR/MWh",
            entries=narwhals.from_native(pandas_frame.reset_index().rename(columns={"index": "timestamp"}))
        )