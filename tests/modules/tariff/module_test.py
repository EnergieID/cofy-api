import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.tariff.module import TariffModule
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from tests.modules.tariff.dummy_source import DummySource


class DummyAPI:
    router = "dummy_router"


@pytest.mark.parametrize(
    "settings, expected_source_type",
    [
        ({"source": DummySource()}, DummySource),
        ({"country_code": "DE", "api_key": "key"}, EntsoeDayAheadTariffSource),
    ],
)
def test_tariffmodule_source_selection(settings, expected_source_type):
    module = TariffModule(settings)
    assert isinstance(module.source, expected_source_type)


def test_tariffmodule_type_property():
    module = TariffModule({"country_code": "DE", "api_key": "key"})
    assert module.type == "tariff"


class TestTariffModule:
    def setup_method(self):
        self.module = TariffModule({"source": DummySource()})
        self.start = dt.datetime(2026, 1, 1, 0, 0)
        self.end = dt.datetime(2026, 1, 1, 3, 0)

    @pytest.mark.asyncio
    async def test_get_tariffs(self):
        # Simulate FastAPI dependency injection
        result = await self.module.get_tariffs(self.start, self.end)
        assert isinstance(result, list)
        assert len(result) == 3
        for i, entry in enumerate(result):
            assert entry.value == i * 10.0
            assert entry.timestamp == self.start + dt.timedelta(hours=i)

    def test_api_endpoint(self):
        app = FastAPI()
        app.include_router(self.module)
        client = TestClient(app)

        response = client.get(
            self.module.prefix,
            params={"start": self.start.isoformat(), "end": self.end.isoformat()},
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        for i, entry in enumerate(data):
            assert entry["value"] == i * 10.0
            assert (
                entry["timestamp"] == (self.start + dt.timedelta(hours=i)).isoformat()
            )
