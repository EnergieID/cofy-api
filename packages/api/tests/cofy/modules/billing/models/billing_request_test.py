import datetime as dt

from cofy.modules.billing.models.billing_request import (
    DataPoint,
)


class TestDataPoint:
    def test_creates_with_valid_fields(self):
        ts = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        dp = DataPoint(timestamp=ts, value=150.5)
        assert dp.timestamp == ts
        assert dp.value == 150.5
