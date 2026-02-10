import datetime as dt
from typing import Annotated

import pytest
from fastapi import FastAPI, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel

from src.shared.timeseries.formats.csv import CSVFormat
from src.shared.timeseries.formats.json import DefaultDataType, JSONFormat
from src.shared.timeseries.module import TimeseriesModule
from tests.shared.timeseries.dummy_source import DummyTimeseriesSource


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
        self.app = FastAPI()
        self.app.include_router(self.module)
        self.client = TestClient(self.app)

    @pytest.mark.asyncio
    async def test_fetch_timeseries(self):
        result = await self.module.source.fetch_timeseries(
            self.start, self.end, dt.timedelta(hours=1)
        )
        assert hasattr(result, "frame")
        df = result.frame
        assert len(df) == 3
        for i, row in enumerate(result.to_arr()):
            assert row["value"] == i * 10.0
            assert row["timestamp"] == self.start + dt.timedelta(hours=i)

    def test_api_endpoint(self):
        response = self.client.get(
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
            self.assert_iso_equals_datetime(
                entry["timestamp"], self.start + dt.timedelta(hours=i)
            )

    def assert_iso_equals_datetime(self, ts1: str, ts2: dt.datetime):
        expected_time = ts2.replace(tzinfo=dt.UTC)
        actual_time = dt.datetime.fromisoformat(ts1.replace("Z", "+00:00"))
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

    def test_no_end_or_limit_should_fail(self):
        app = FastAPI()
        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "default_args": {"limit": None, "end": lambda: None},
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(
            module.prefix,
            params={"start": self.start.isoformat()},
        )
        assert response.status_code == 422

    def test_end_before_start_should_fail(self):
        response = self.client.get(
            self.module.prefix,
            params={
                "start": self.end.isoformat(),
                "end": self.start.isoformat(),
            },
        )
        assert response.status_code == 422

    def test_no_start_should_fail(self):
        app = FastAPI()
        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "default_args": {"limit": None, "start": lambda: None},
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(
            module.prefix,
            params={"end": self.end.isoformat()},
        )
        assert response.status_code == 422

    def test_no_resolution_should_fail(self):
        app = FastAPI()
        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "default_args": {"limit": None, "resolution": None},
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(
            module.prefix,
            params={
                "start": self.start.isoformat(),
                "end": self.end.isoformat(),
            },
        )
        assert response.status_code == 422

    def test_resolution_should_be_in_supported_resolutions(self):
        app = FastAPI()
        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "supported_resolutions": ["PT15M", "PT1H"],
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(
            module.prefix,
            params={
                "start": self.start.isoformat(),
                "end": self.end.isoformat(),
                "resolution": "PT30M",
            },
        )
        assert response.status_code == 422

    def test_should_use_defaults_if_not_provided(self):
        app = FastAPI()
        module = TimeseriesModule(
            {
                "source": DummyTimeseriesSource(),
                "default_args": {
                    "start": lambda: self.start,
                    "end": lambda: self.end,
                    "limit": None,
                },
            }
        )
        app.include_router(module)
        client = TestClient(app)

        response = client.get(module.prefix)
        assert response.status_code == 200
        result = response.json()
        self.assert_iso_equals_datetime(result["metadata"]["start"], self.start)
        self.assert_iso_equals_datetime(result["metadata"]["end"], self.end)

    def test_utc_used_if_no_timezone(self):
        start_naive = self.start.replace(tzinfo=None)
        end_naive = self.end.replace(tzinfo=None)

        response = self.client.get(
            self.module.prefix,
            params={
                "start": start_naive.isoformat(),
                "end": end_naive.isoformat(),
            },
        )
        assert response.status_code == 200
        result = response.json()
        data = result.get("data")
        assert len(data) == 3
        self.assert_iso_equals_datetime(result["metadata"]["start"], self.start)
        self.assert_iso_equals_datetime(result["metadata"]["end"], self.end)

    def test_offset_and_limit(self):
        response = self.client.get(
            self.module.prefix,
            params={
                "start": self.start.isoformat(),
                "offset": 1,
                "limit": 1,
            },
        )
        assert response.status_code == 200
        result = response.json()
        data = result.get("data")
        assert len(data) == 1
        self.assert_iso_equals_datetime(
            result["metadata"]["start"], self.start + dt.timedelta(hours=1)
        )
        self.assert_iso_equals_datetime(
            result["metadata"]["end"], self.start + dt.timedelta(hours=2)
        )

    def test_csv_format(self):
        response = self.client.get(
            f"{self.module.prefix}.csv",
            params={
                "start": self.start.isoformat(),
                "end": self.end.isoformat(),
            },
        )
        assert response.status_code == 200
        csv_content = response.content.decode()
        lines = csv_content.strip().split("\n")
        assert lines[0] == "timestamp,value"
        assert len(lines) == 4

    def test_multiple_resolutions(self):
        response = self.client.get(
            self.module.prefix,
            params={
                "start": self.start.isoformat(),
                "end": self.end.isoformat(),
                "resolution": "PT30M",
            },
        )
        assert response.status_code == 200
        result = response.json()
        data = result.get("data")
        assert len(data) == 6
        for i, entry in enumerate(data):
            assert entry["value"] == i * 10.0
            self.assert_iso_equals_datetime(
                entry["timestamp"], self.start + dt.timedelta(minutes=30 * i)
            )

    def test_can_use_resolution_with_limit(self):
        response = self.client.get(
            self.module.prefix,
            params={
                "start": self.start.isoformat(),
                "resolution": "PT30M",
                "limit": 2,
            },
        )
        assert response.status_code == 200
        result = response.json()
        data = result.get("data")
        assert len(data) == 2
        for i, entry in enumerate(data):
            assert entry["value"] == i * 10.0
            self.assert_iso_equals_datetime(
                entry["timestamp"], self.start + dt.timedelta(minutes=30 * i)
            )

    @pytest.mark.parametrize(
        "resolution, limit, start, end",
        [
            (
                "PT15M",
                2,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2026, 1, 1, 0, 30, tzinfo=dt.UTC),
            ),
            (
                "PT30M",
                3,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2026, 1, 1, 1, 30, tzinfo=dt.UTC),
            ),
            (
                "PT1H",
                2,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2026, 1, 1, 2, 0, tzinfo=dt.UTC),
            ),
            (
                "P1D",
                1,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2026, 1, 2, 0, 0, tzinfo=dt.UTC),
            ),
            (
                "P7D",
                15,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2026, 4, 16, 0, 0, tzinfo=dt.UTC),
            ),
            (
                "P1M",
                14,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2027, 3, 1, 0, 0, tzinfo=dt.UTC),
            ),
            (
                "P1Y",
                10,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2036, 1, 1, 0, 0, tzinfo=dt.UTC),
            ),
            (
                "P1Y2M3DT4H5M6S",
                2,
                dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
                dt.datetime(2028, 5, 7, 8, 10, 12, tzinfo=dt.UTC),
            ),
        ],
    )
    def test_resolution_limit_and_start_determine_end(
        self, resolution, limit, start, end
    ):
        response = self.client.get(
            self.module.prefix,
            params={
                "start": start.isoformat(),
                "resolution": resolution,
                "limit": limit,
            },
        )
        assert response.status_code == 200
        result = response.json()
        data = result.get("data")
        assert len(data) == limit
        self.assert_iso_equals_datetime(result["metadata"]["end"], end)
