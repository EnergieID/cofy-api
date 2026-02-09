import datetime as dt
from importlib import resources
from unittest.mock import MagicMock

import narwhals as nw
import pandas as pd
import pytest

from src.modules.tariff.model import TariffFrame
from src.modules.tariff.sources.entsoe_day_ahead import EntsoeDayAheadTariffSource

EXAMPLE_CSV_NAME = "entsoe_day_ahead_example.csv"
EXAMPLE_CSV_PATH = resources.files("tests.modules.tariff.sources").joinpath(
    EXAMPLE_CSV_NAME
)


def test_init_valid():
    src = EntsoeDayAheadTariffSource("DE", "key")
    assert src.country_code == "DE"
    assert hasattr(src, "client")


@pytest.mark.parametrize(
    "country_code, api_key, error_msg",
    [
        (None, "key", "country_code must be provided"),
        ("DE", None, "api_key must be provided"),
        ("", "key", "country_code must be provided"),
        ("DE", "", "api_key must be provided"),
    ],
)
def test_init_invalid(country_code, api_key, error_msg):
    with pytest.raises(ValueError, match=error_msg):
        EntsoeDayAheadTariffSource(country_code, api_key)


@pytest.mark.asyncio
async def test_fetch_tariffs():
    src = EntsoeDayAheadTariffSource("BE", "key")
    src.client = MagicMock()
    src.client.query_day_ahead_prices.return_value = (
        pd.read_csv(
            str(EXAMPLE_CSV_PATH),
            index_col=0,
            parse_dates=True,
        )
        .squeeze()
        .rename(0)  # ty: ignore[possibly-missing-attribute, no-matching-overload]
    )

    start = dt.datetime(2026, 1, 21)
    end = dt.datetime(2026, 1, 22)
    result = await src.fetch_tariffs(start, end)
    assert isinstance(result, TariffFrame)
    assert result.unit == "EUR/MWh"
    assert result.entries.schema == {
        "value": nw.Float64,
        "timestamp": nw.Datetime,
    }

    # Check specific tariff value
    ts = pd.Timestamp("2026-01-21 16:45:00+01:00")
    filtered = result.entries.filter(nw.col("timestamp") == ts)
    first = list(filtered.iter_rows(named=True))[0]
    assert first["value"] == 111.45
