import datetime as dt

from cofy.modules.timeseries import (
    TimeseriesModule,
)


def floor_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Floor a datetime object to the nearest lower multiple of delta."""
    seconds = (dt_obj - dt.datetime.min.replace(tzinfo=dt_obj.tzinfo)).total_seconds()
    floored_seconds = seconds - (seconds % delta.total_seconds())
    return dt.datetime.min.replace(tzinfo=dt_obj.tzinfo) + dt.timedelta(seconds=floored_seconds)


class TariffModule(TimeseriesModule):
    type: str = "tariff"
    type_description: str = "Module providing tariff data as time series."

    @property
    def default_args(self):
        return {
            "start": lambda: floor_datetime(dt.datetime.now(dt.UTC), dt.timedelta(minutes=15)),
            "end": lambda: None,
            "offset": 0,
            "limit": 288,
            "resolution": "PT15M",
        }
