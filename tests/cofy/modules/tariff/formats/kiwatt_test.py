import datetime as dt
from datetime import UTC, timedelta
from unittest.mock import patch

import pandas as pd

from cofy.modules.tariff import (
    KiwattFormat,
    PriceRecordModel,
    ResponseModel,
    to_utc_timestring,
)
from cofy.modules.timeseries import Timeseries


def _make_timeseries(start: dt.datetime, end: dt.datetime, resolution: timedelta = timedelta(hours=1)) -> Timeseries:
    steps = int((end - start) / resolution)
    data = [{"timestamp": start + resolution * i, "value": 10.0 + i} for i in range(steps)]
    return Timeseries(
        frame=pd.DataFrame(data),
        metadata={
            "start": start,
            "end": end,
            "unit": "EUR/MWh",
            "resolution": resolution,
        },
    )


class TestToUtcTimestring:
    def test_datetime_input(self):
        dt_obj = dt.datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        assert to_utc_timestring(dt_obj) == "2026-01-01T12:00:00+00:00"

    def test_string_input(self):
        result = to_utc_timestring("2026-01-01T12:00:00+00:00")
        assert result == "2026-01-01T12:00:00+00:00"

    def test_non_utc_datetime_converts_to_utc(self):
        cet = dt.timezone(timedelta(hours=1))
        dt_obj = dt.datetime(2026, 1, 1, 13, 0, 0, tzinfo=cet)
        assert to_utc_timestring(dt_obj) == "2026-01-01T12:00:00+00:00"

    def test_microseconds_are_stripped(self):
        dt_obj = dt.datetime(2026, 1, 1, 12, 0, 0, 123456, tzinfo=UTC)
        assert to_utc_timestring(dt_obj) == "2026-01-01T12:00:00+00:00"

    def test_non_utc_string_converts_to_utc(self):
        result = to_utc_timestring("2026-01-01T13:00:00+01:00")
        assert result == "2026-01-01T12:00:00+00:00"


class TestKiwattFormat:
    def setup_method(self):
        self.patcher = patch("cofy.modules.tariff.formats.kiwatt.datetime")
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.now.return_value = dt.datetime(2026, 1, 1, 11, 15, 0, tzinfo=UTC)
        self.mock_datetime.fromisoformat = dt.datetime.fromisoformat
        self.mock_datetime.side_effect = lambda *args, **kw: dt.datetime(*args, **kw)

    def teardown_method(self):
        self.patcher.stop()

    def test_return_type(self):
        fmt = KiwattFormat()
        assert fmt.ReturnType == ResponseModel

    def test_format_basic(self):
        start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 1, 1, 3, 0, tzinfo=UTC)
        ts = _make_timeseries(start, end)

        fmt = KiwattFormat()
        result = fmt.format(ts)

        assert isinstance(result, ResponseModel)
        assert result.generatedAtUTC == "2026-01-01T11:15:00+00:00"
        assert result.periodStartUTC == "2026-01-01T00:00:00+00:00"
        assert result.periodEndUTC == "2026-01-01T03:00:00+00:00"
        assert result.source == "Cofy-API-Demo"
        assert result.unit == "EUR/MWh"
        assert result.resolution == timedelta(hours=1)

    def test_format_prices(self):
        start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 1, 1, 3, 0, tzinfo=UTC)
        ts = _make_timeseries(start, end)

        result = KiwattFormat().format(ts)

        assert len(result.prices) == 3
        assert all(isinstance(p, PriceRecordModel) for p in result.prices)
        assert result.prices[0].startUTC == "2026-01-01T00:00:00+00:00"
        assert result.prices[0].value == 10.0
        assert result.prices[1].startUTC == "2026-01-01T01:00:00+00:00"
        assert result.prices[1].value == 11.0
        assert result.prices[2].startUTC == "2026-01-01T02:00:00+00:00"
        assert result.prices[2].value == 12.0

    def test_format_with_15min_resolution(self):
        start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
        ts = _make_timeseries(start, end, resolution=timedelta(minutes=15))

        result = KiwattFormat().format(ts)

        assert len(result.prices) == 4
        assert result.resolution == timedelta(minutes=15)
        assert result.prices[1].startUTC == "2026-01-01T00:15:00+00:00"

    def test_format_custom_source(self):
        start = dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
        end = dt.datetime(2026, 1, 1, 1, 0, tzinfo=UTC)
        ts = _make_timeseries(start, end)

        result = KiwattFormat(source="MySource").format(ts)
        assert result.source == "MySource"
