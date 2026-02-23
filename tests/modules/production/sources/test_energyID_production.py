import datetime as dt
import json
from importlib import resources
from unittest.mock import MagicMock, patch

import narwhals as nw
import pytest

from src.modules.production.sources.energyID_production import EnergyIDProduction

EXAMPLE_JSON_NAME = "energyID_production_example.json"
EXAMPLE_JSON_PATH = resources.files("tests.modules.production.sources").joinpath(EXAMPLE_JSON_NAME)
# Load the example JSON response
with open(str(EXAMPLE_JSON_PATH)) as f:
    EXAMPLE_JSON = json.load(f)


@pytest.fixture
def mock_requests_get():
    """Fixture to mock requests.get for both API key check and data fetch."""

    def _mocked_requests_get(url, headers=None, *args, **kwargs):
        # API key check endpoint
        if url.startswith("https://api.energyid.eu/api/v1/members/me"):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            return mock_resp
        # Data fetch endpoint
        elif url.startswith("https://api.energyid.eu/api/v1/records/"):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = EXAMPLE_JSON
            return mock_resp
        else:
            raise ValueError(f"Unexpected URL: {url}")

    with patch("requests.get", side_effect=_mocked_requests_get):
        yield


@pytest.mark.asyncio
async def test_fetch_timeseries_success(mock_requests_get):
    api_key = "dummy_key"
    record_id = "dummy_record"
    source = EnergyIDProduction(api_key, record_id)
    start = dt.datetime(2026, 2, 9, 0, 0)
    end = dt.datetime(2026, 2, 10, 0, 0)
    resolution = dt.timedelta(hours=1)
    ts = await source.fetch_timeseries(start, end, resolution)

    # Validate the returned Timeseries object
    assert isinstance(ts.frame, nw.DataFrame)
    assert ts.metadata["unit"] == "kWh"
    # Check that the DataFrame has the expected number of rows and columns
    assert ts.frame.shape[0] == 24
    assert set(ts.frame.columns) == {"timestamp", "value"}
    # Check a sample value
    row = ts.frame.row(0)
    assert row[1] == 0.000655
    assert row[0] == dt.datetime.fromisoformat("2026-02-09T00:00:00+01:00")


@pytest.mark.asyncio
async def test_fetch_timeseries_invalid_api_key():
    def _mocked_requests_get(url, headers=None, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        return mock_resp

    with (
        patch("requests.get", side_effect=_mocked_requests_get),
        pytest.raises(ValueError, match="Invalid API key"),
    ):
        EnergyIDProduction("bad_key", "dummy_record")


@pytest.mark.asyncio
async def test_fetch_timeseries_api_error(mock_requests_get):
    api_key = "dummy_key"
    record_id = "dummy_record"
    source = EnergyIDProduction(api_key, record_id)
    start = dt.datetime(2026, 2, 9, 0, 0)
    end = dt.datetime(2026, 2, 10, 0, 0)
    resolution = dt.timedelta(hours=1)

    # Mock the data fetch to return an error
    def _mocked_requests_get(url, headers=None, *args, **kwargs):
        if url.startswith("https://api.energyid.eu/api/v1/records/"):
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            return mock_resp

    with (
        patch("requests.get", side_effect=_mocked_requests_get),
        pytest.raises(ValueError, match="Failed to fetch data from EnergyID API"),
    ):
        await source.fetch_timeseries(start, end, resolution)


@pytest.mark.asyncio
async def test_fetch_timeseries_invalid_resolution(mock_requests_get):
    api_key = "dummy_key"
    record_id = "dummy_record"
    source = EnergyIDProduction(api_key, record_id)
    start = dt.datetime(2026, 2, 9, 0, 0)
    end = dt.datetime(2026, 2, 10, 0, 0)
    bad_resolution = dt.timedelta(hours=2)
    with pytest.raises(AssertionError, match="Resolution PT2H is not supported"):
        await source.fetch_timeseries(start, end, bad_resolution)
