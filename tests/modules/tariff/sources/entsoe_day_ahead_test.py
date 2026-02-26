import datetime as dt
from importlib import resources
from unittest.mock import MagicMock

import narwhals as nw
import pandas as pd
import pytest
from entsoe.exceptions import NoMatchingDataError

from cofy.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource
from cofy.modules.timeseries.model import Timeseries

EXAMPLE_CSV_NAME = "entsoe_day_ahead_example.csv"
EXAMPLE_CSV_PATH = resources.files("tests.modules.tariff.sources").joinpath(EXAMPLE_CSV_NAME)


def test_init_valid():
    src = EntsoeDayAheadTariffSource("key", "DE")
    assert src.country_code == "DE"
    assert hasattr(src, "client")


@pytest.mark.parametrize(
    "api_key, country_code, error_msg",
    [
        (None, "DE", "api_key must be provided"),
        ("", "DE", "api_key must be provided"),
    ],
)
def test_init_invalid(api_key, country_code, error_msg):
    with pytest.raises(ValueError, match=error_msg):
        EntsoeDayAheadTariffSource(api_key, country_code)


@pytest.mark.asyncio
async def test_fetch_timeseries():
    src = EntsoeDayAheadTariffSource("key", "BE")
    src.client = MagicMock()
    src.client.query_day_ahead_prices.return_value = (
        pd.read_csv(
            str(EXAMPLE_CSV_PATH),
            index_col=0,
            parse_dates=True,
        )
        .squeeze()
        .rename(0)  # ty: ignore[unresolved-attribute, no-matching-overload]
    )

    start = dt.datetime(2026, 1, 21)
    end = dt.datetime(2026, 1, 22)
    result = await src.fetch_timeseries(start, end)
    assert isinstance(result, Timeseries)
    assert result.metadata["unit"] == "EUR/MWh"
    assert result.frame.schema == {
        "value": nw.Float64,
        "timestamp": nw.Datetime,
    }

    # Check specific tariff value
    ts = pd.Timestamp("2026-01-21 16:45:00+01:00")
    filtered = result.frame.filter(nw.col("timestamp") == ts)
    first = list(filtered.iter_rows(named=True))[0]
    assert first["value"] == 111.45


@pytest.mark.asyncio
async def test_returns_empty_when_no_data():
    src = EntsoeDayAheadTariffSource("key", "BE")
    src.client = MagicMock()
    src.client.query_day_ahead_prices.side_effect = NoMatchingDataError("No data")

    start = dt.datetime(2026, 1, 21)
    end = dt.datetime(2026, 1, 22)
    result = await src.fetch_timeseries(start, end)
    assert isinstance(result, Timeseries)
    assert result.frame.is_empty
