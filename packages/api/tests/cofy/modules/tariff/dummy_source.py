from cofy.modules.tariff import PriceSource
from cofy.modules.timeseries import Timeseries
from tests.cofy.modules.timeseries.dummy_source import DummyTimeseriesSource


class DummySource(DummyTimeseriesSource, PriceSource):
    async def _fetch_timeseries(self, *args, **kwargs) -> Timeseries:
        ts = await super()._fetch_timeseries(*args, **kwargs)
        # Add some dummy metadata
        ts.metadata["unit"] = "EUR/MWh"
        return ts
