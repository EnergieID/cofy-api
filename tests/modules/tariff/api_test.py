import datetime as dt

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.tariff.api import TariffAPI
from tests.modules.tariff.dummy_source import DummySource


class TestTariffAPI:
    def setup_method(self):
        self.api = TariffAPI(DummySource())
        self.start = dt.datetime(2026, 1, 1, 0, 0)
        self.end = dt.datetime(2026, 1, 1, 3, 0)

    @pytest.mark.asyncio
    async def test_get_tariffs(self):
        # Simulate FastAPI dependency injection
        result = await self.api.get_tariffs(self.start, self.end)
        assert isinstance(result, list)
        assert len(result) == 3
        for i, entry in enumerate(result):
            assert entry.value == i * 10.0
            assert entry.timestamp == self.start + dt.timedelta(hours=i)

    def test_api_endpoint(self):
        app = FastAPI()
        app.include_router(self.api.router)
        client = TestClient(app)

        response = client.get(
            "/v0/",
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
