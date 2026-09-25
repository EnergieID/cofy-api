import datetime as dt

from cofy.modules.timeseries import ceil_datetime, floor_datetime


def test_floor_datetime():
    dt_obj = dt.datetime(2026, 1, 1, 10, 37, 45, tzinfo=dt.UTC)
    assert floor_datetime(dt_obj, dt.timedelta(hours=1)) == dt.datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt.UTC)


def test_ceil_datetime():
    dt_obj = dt.datetime(2026, 1, 1, 10, 37, 45, tzinfo=dt.UTC)
    assert ceil_datetime(dt_obj, dt.timedelta(minutes=15)) == dt.datetime(2026, 1, 1, 10, 45, tzinfo=dt.UTC)


def test_ceil_datetime_keeps_aligned_value():
    dt_obj = dt.datetime(2026, 1, 1, 10, 45, tzinfo=dt.UTC)
    assert ceil_datetime(dt_obj, dt.timedelta(minutes=15)) == dt_obj
