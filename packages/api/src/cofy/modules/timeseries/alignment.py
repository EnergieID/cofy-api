import datetime as dt


def floor_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Floor a datetime object to the nearest lower multiple of delta."""
    seconds = (dt_obj - dt.datetime.min.replace(tzinfo=dt_obj.tzinfo)).total_seconds()
    floored_seconds = seconds - (seconds % delta.total_seconds())
    return dt.datetime.min.replace(tzinfo=dt_obj.tzinfo) + dt.timedelta(seconds=floored_seconds)


def ceil_datetime(dt_obj: dt.datetime, delta: dt.timedelta) -> dt.datetime:
    """Ceil a datetime object to the nearest higher multiple of delta."""
    floored = floor_datetime(dt_obj, delta)
    return floored if floored == dt_obj else floored + delta
