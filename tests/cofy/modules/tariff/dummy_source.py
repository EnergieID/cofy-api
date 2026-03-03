from cofy.modules.timeseries import Timeseries
from tests.cofy.modules.timeseries.dummy_source import DummyTimeseriesSource


class DummySource(DummyTimeseriesSource):
    async def fetch_timeseries(self, *args, **kwargs) -> Timeseries:
        ts = await super().fetch_timeseries(*args, **kwargs)
        # Add some dummy metadata
        ts.metadata["unit"] = "EUR/MWh"
        return ts
