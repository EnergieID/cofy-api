import datetime as dt
from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.shared.timeseries.formats.csv import CSVFormat
from src.shared.timeseries.formats.json import DefaultDataType, JSONFormat
from src.shared.timeseries.model import Timeseries
from src.shared.timeseries.module import TimeseriesModule
from src.shared.timeseries.source import TimeseriesSource


class DummyTimeseriesSource(TimeseriesSource):
    async def fetch_timeseries(self, start: dt.datetime, end: dt.datetime, **kwargs):
        import pandas as pd

        data = [
            {"timestamp": start + dt.timedelta(hours=i), "value": i * 10.0}
            for i in range(int((end - start).total_seconds() // 3600))
        ]
        frame = pd.DataFrame(data)
        return Timeseries(metadata={"foo": "bar", **kwargs}, frame=frame)


@pytest.mark.parametrize(
    "settings, expected_source_type",
    [
        ({"source": DummyTimeseriesSource()}, DummyTimeseriesSource),
    ],
)
def test_timeseriesmodule_source_selection(settings, expected_source_type):
    module = TimeseriesModule(settings)
    assert isinstance(module.source, expected_source_type)


def test_timeseriesmodule_type_property():
    module = TimeseriesModule({"source": DummyTimeseriesSource()})
    assert module.type == "timeseries"


def test_formats_default():
    module = TimeseriesModule({"source": DummyTimeseriesSource()})
    assert any(isinstance(fmt, JSONFormat) for fmt in module.formats)
    assert any(isinstance(fmt, CSVFormat) for fmt in module.formats)


class TestTimeseriesModule:
    def setup_method(self):
        self.module = TimeseriesModule(
            {"source": DummyTimeseriesSource(), "default_args": {"limit": None}}
        )
        self.start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC)
        self.end = dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC)

    @pytest.mark.asyncio
    async def test_fetch_timeseries(self):
        result = await self.module.source.fetch_timeseries(self.start, self.end)
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
        assert len(data) == 3
        for i, entry in enumerate(data):
            assert entry["value"] == i * 10.0
            # Normalize timestamp for comparison
            expected_time = (self.start + dt.timedelta(hours=i)).replace(tzinfo=dt.UTC)
            actual_time = dt.datetime.fromisoformat(
                entry["timestamp"].replace("Z", "+00:00")
            )
            assert actual_time == expected_time

    def test_can_create_extra_args(self):
        app = FastAPI()

        class CustomMetadataType(BaseModel):
            foo: str
            fas: int

        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "extra_args": {
                    "foo": Annotated[
                        str, Query(description="Extra argument for testing")
                    ],
                    "fas": Annotated[
                        int, Query(default=42, description="Another extra argument")
                    ],
                },
                "formats": [
                    JSONFormat[DefaultDataType, CustomMetadataType](
                        DefaultDataType, CustomMetadataType
                    )
                ],
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(
            module.prefix,
            params={"foo": "baz"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["metadata"] == {"foo": "baz", "fas": 42}
