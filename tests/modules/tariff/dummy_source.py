from src.shared.timeseries.model import Timeseries
from tests.shared.timeseries.dummy_source import DummyTimeseriesSource


class DummySource(DummyTimeseriesSource):
    async def fetch_timeseries(self, *args, **kwargs) -> Timeseries:
        ts = await super().fetch_timeseries(*args, **kwargs)
        # Add some dummy metadata
        ts.metadata["unit"] = "EUR/MWh"
        return ts
