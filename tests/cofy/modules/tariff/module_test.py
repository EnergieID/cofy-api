import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.modules.tariff import EntsoeDayAheadTariffSource, TariffModule
from tests.cofy.modules.tariff.dummy_source import DummySource


def test_if_no_country_code_specified_extra_args_is_set():
    module = TariffModule(source=EntsoeDayAheadTariffSource(api_key="key"))
    assert "country_code" in module.DynamicParameters.model_fields


def test_tariffmodule_type_property():
    module = TariffModule(source=EntsoeDayAheadTariffSource(api_key="key"))
    assert module.type == "tariff"


def test_floor_datetime():
    from cofy.modules.tariff.module import floor_datetime

    dt_obj = dt.datetime(2026, 1, 1, 10, 37, 45, tzinfo=dt.UTC)
    delta = dt.timedelta(hours=1)
    floored = floor_datetime(dt_obj, delta)
    assert floored == dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.UTC)


class TestTariffModule:
    def setup_method(self):
        self.module = TariffModule(source=DummySource(), default_args={"limit": None})
        self.start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
        self.end = dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC)

    @pytest.mark.asyncio
    async def test_fetch_timeseries(self):
        # The DummySource returns a TariffFrame with a DataFrame
        result = await self.module.source.fetch_timeseries(self.start, self.end, resolution=dt.timedelta(hours=1))
        assert hasattr(result, "frame")
        df = result.frame
        assert len(df) == 3
        for i, row in enumerate(result.to_arr()):
            assert row["value"] == i * 10.0
            assert row["timestamp"] == self.start + dt.timedelta(hours=i)

    def test_api_endpoint(self):
        app = FastAPI()
        app.include_router(self.module)
        client = TestClient(app)

        response = client.get(
            self.module.prefix,
            params={"start": self.start.isoformat(), "end": self.end.isoformat()},
        )
        assert response.status_code == 200
        result = response.json()
        assert isinstance(result, dict)
        assert "data" in result
        data = result.get("data")
        assert len(data) == 12
        for i, entry in enumerate(data):
            assert entry["value"] == i * 10.0
            assert dt.datetime.fromisoformat(entry["timestamp"]) == self.start + dt.timedelta(minutes=15 * i)
