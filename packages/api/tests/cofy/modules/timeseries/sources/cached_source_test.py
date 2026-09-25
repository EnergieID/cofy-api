import asyncio
import datetime as dt
from types import SimpleNamespace

import pandas as pd
import polars as pl
import pytest
import yaml
from isodate import Duration
from pydantic import ValidationError

from cofy.api import finalize
from cofy.modules.timeseries import (
    CachedTimeseriesSource,
    CachedTimeseriesSourceSettings,
    Timeseries,
    TimeseriesSource,
)
from cofy.modules.timeseries.sources import cached_source

from ..dummy_source import DummyTimeseriesSource

DAY = dt.timedelta(days=1)
HOUR = dt.timedelta(hours=1)
T0 = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)


class CountingSource(TimeseriesSource):
    """Records every requested range and returns one row per resolution step, valued by its hour offset from T0."""

    def __init__(self, max_age: dt.timedelta | None = HOUR, backend: str = "pandas", margin: dt.timedelta = DAY * 0):
        self.calls: list[tuple[dt.datetime, dt.datetime]] = []
        self.fail = False
        self.delay = 0.0
        self._max_age = max_age
        self.backend = backend
        self.margin = margin

    async def fetch_timeseries(self, start, end, resolution, **kwargs) -> Timeseries:
        self.calls.append((start, end))
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("upstream down")

        timestamps = []
        current = start - self.margin
        while current < end + self.margin:
            timestamps.append(current)
            current += resolution
        values = [(ts - T0) / HOUR for ts in timestamps]

        if self.backend == "polars":
            return Timeseries(frame=pl.DataFrame({"timestamp": timestamps, "value": values}), metadata={"unit": "x"})
        brussels = pd.DatetimeIndex(timestamps).tz_convert("Europe/Brussels")
        return Timeseries(frame=pd.DataFrame({"timestamp": brussels, "value": values}), metadata={"unit": "x"})

    @property
    def max_age(self) -> dt.timedelta | None:
        return self._max_age


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    now = [1000.0]
    # patch only the cache's clock: asyncio's event loop relies on the real time.monotonic
    monkeypatch.setattr(cached_source, "time", SimpleNamespace(monotonic=lambda: now[0]))
    return now


def values(timeseries: Timeseries) -> list[float]:
    return [row["value"] for row in timeseries.to_arr()]


def hours(start: int, end: int) -> list[float]:
    return [float(h) for h in range(start, end)]


@pytest.mark.asyncio
async def test_hit_within_max_age_does_not_refetch(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    first = await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    second = await source.fetch_timeseries(T0, T0 + DAY, HOUR)

    assert values(first) == values(second) == hours(0, 24)
    assert upstream.calls == [(T0, T0 + DAY)]


@pytest.mark.asyncio
async def test_only_expired_chunks_are_refetched(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    clock[0] += 1800
    await source.fetch_timeseries(T0 + DAY, T0 + 2 * DAY, HOUR)
    clock[0] += 1800
    await source.fetch_timeseries(T0, T0 + 2 * DAY, HOUR)

    assert upstream.calls == [(T0, T0 + DAY), (T0 + DAY, T0 + 2 * DAY), (T0, T0 + DAY)]


@pytest.mark.asyncio
async def test_sliding_window_fetches_only_new_chunk(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + 3 * DAY, HOUR)
    result = await source.fetch_timeseries(T0 + DAY, T0 + 4 * DAY, HOUR)

    assert values(result) == hours(24, 96)
    assert upstream.calls == [(T0, T0 + 3 * DAY), (T0 + 3 * DAY, T0 + 4 * DAY)]


@pytest.mark.asyncio
async def test_sub_range_is_served_from_cache(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + 7 * DAY, HOUR)
    result = await source.fetch_timeseries(T0 + DAY + 3 * HOUR, T0 + 2 * DAY + 5 * HOUR, HOUR)

    assert values(result) == hours(27, 53)
    assert len(upstream.calls) == 1


@pytest.mark.asyncio
async def test_separated_gaps_are_fetched_separately(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0 + DAY, T0 + 2 * DAY, HOUR)
    result = await source.fetch_timeseries(T0, T0 + 3 * DAY, HOUR)

    assert values(result) == hours(0, 72)
    assert sorted(upstream.calls[1:]) == [(T0, T0 + DAY), (T0 + 2 * DAY, T0 + 3 * DAY)]


@pytest.mark.asyncio
async def test_rows_outside_requested_range_are_sliced_off(clock):
    upstream = CountingSource(margin=2 * HOUR)
    source = CachedTimeseriesSource(upstream)

    result = await source.fetch_timeseries(T0 + 2 * HOUR, T0 + 5 * HOUR, HOUR)

    assert values(result) == hours(2, 5)


@pytest.mark.asyncio
async def test_empty_chunks_are_cached(clock):
    class EmptySource(CountingSource):
        async def fetch_timeseries(self, start, end, resolution, **kwargs) -> Timeseries:
            self.calls.append((start, end))
            return Timeseries(frame=pd.DataFrame({"timestamp": [], "value": []}))

    upstream = EmptySource()
    source = CachedTimeseriesSource(upstream)

    assert values(await source.fetch_timeseries(T0, T0 + DAY, HOUR)) == []
    assert values(await source.fetch_timeseries(T0, T0 + DAY, HOUR)) == []
    assert len(upstream.calls) == 1


@pytest.mark.asyncio
async def test_kwargs_and_resolutions_do_not_share_chunks(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + DAY, HOUR, country_code="BE")
    await source.fetch_timeseries(T0, T0 + DAY, HOUR, country_code="NL")
    await source.fetch_timeseries(T0, T0 + DAY, dt.timedelta(minutes=15), country_code="BE")

    assert len(upstream.calls) == 3


@pytest.mark.asyncio
async def test_unaligned_requests_are_cached_for_their_exact_range(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)
    start = T0 + dt.timedelta(minutes=7)

    await source.fetch_timeseries(start, T0 + DAY, HOUR)
    await source.fetch_timeseries(start, T0 + DAY, HOUR)

    assert upstream.calls == [(start, T0 + DAY)]


@pytest.mark.asyncio
async def test_month_resolution_is_cached_for_its_exact_range(clock):
    upstream = DummyTimeseriesSource()
    source = CachedTimeseriesSource(upstream, max_age=HOUR)

    result = await source.fetch_timeseries(T0, T0 + 3 * DAY, dt.timedelta(days=1))
    monthly = await source.fetch_timeseries(T0, T0 + 3 * DAY, Duration(months=1))

    assert len(values(result)) == 3
    assert list(source._entries)[-1][1:] == (T0, T0 + 3 * DAY)
    assert len(values(monthly)) == 1


@pytest.mark.asyncio
async def test_concurrent_misses_share_one_upstream_call(clock):
    upstream = CountingSource()
    upstream.delay = 0.01
    source = CachedTimeseriesSource(upstream)

    first, second = await asyncio.gather(
        source.fetch_timeseries(T0, T0 + DAY, HOUR),
        source.fetch_timeseries(T0, T0 + DAY, HOUR),
    )

    assert values(first) == values(second)
    assert len(upstream.calls) == 1


@pytest.mark.asyncio
async def test_stale_chunks_are_served_when_upstream_fails(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    clock[0] += 7200
    upstream.fail = True
    result = await source.fetch_timeseries(T0, T0 + DAY, HOUR)

    assert values(result) == hours(0, 24)
    assert len(upstream.calls) == 2


@pytest.mark.asyncio
async def test_upstream_error_is_raised_without_cached_data(clock):
    upstream = CountingSource()
    upstream.fail = True
    source = CachedTimeseriesSource(upstream)

    with pytest.raises(RuntimeError, match="upstream down"):
        await source.fetch_timeseries(T0, T0 + DAY, HOUR)


@pytest.mark.asyncio
async def test_least_recently_used_chunks_are_evicted(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream, max_chunks=2)

    await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    await source.fetch_timeseries(T0 + DAY, T0 + 2 * DAY, HOUR)
    await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    await source.fetch_timeseries(T0 + 2 * DAY, T0 + 3 * DAY, HOUR)
    await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    await source.fetch_timeseries(T0 + DAY, T0 + 2 * DAY, HOUR)

    assert upstream.calls[-1] == (T0 + DAY, T0 + 2 * DAY)
    assert len(upstream.calls) == 4


@pytest.mark.asyncio
async def test_request_larger_than_max_chunks_is_still_complete(clock):
    source = CachedTimeseriesSource(CountingSource(), max_chunks=1)

    result = await source.fetch_timeseries(T0, T0 + 3 * DAY, HOUR)

    assert values(result) == hours(0, 72)


@pytest.mark.asyncio
async def test_polars_frames_are_supported(clock):
    upstream = CountingSource(backend="polars")
    source = CachedTimeseriesSource(upstream)

    await source.fetch_timeseries(T0, T0 + 2 * DAY, HOUR)
    result = await source.fetch_timeseries(T0 + 6 * HOUR, T0 + 30 * HOUR, HOUR)

    assert values(result) == hours(6, 30)
    assert len(upstream.calls) == 1


@pytest.mark.asyncio
async def test_non_utc_request_bounds_share_the_utc_chunks(clock):
    upstream = CountingSource()
    source = CachedTimeseriesSource(upstream)
    plus_one = dt.timezone(dt.timedelta(hours=1))

    await source.fetch_timeseries(T0, T0 + 2 * DAY, HOUR)
    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 1, tzinfo=plus_one), dt.datetime(2026, 1, 2, 1, tzinfo=plus_one), HOUR
    )

    assert values(result) == hours(0, 24)
    assert len(upstream.calls) == 1


@pytest.mark.asyncio
async def test_mutating_returned_metadata_does_not_affect_cache(clock):
    source = CachedTimeseriesSource(CountingSource())

    first = await source.fetch_timeseries(T0, T0 + DAY, HOUR)
    first.metadata["unit"] = "changed"
    second = await source.fetch_timeseries(T0, T0 + DAY, HOUR)

    assert second.metadata["unit"] == "x"


def test_max_age_is_inherited_from_wrapped_source():
    assert CachedTimeseriesSource(CountingSource(max_age=HOUR)).max_age == HOUR


def test_max_age_setting_overrides_wrapped_source():
    assert CachedTimeseriesSource(CountingSource(max_age=HOUR), max_age=DAY).max_age == DAY


def test_max_age_is_required_when_wrapped_source_has_none():
    with pytest.raises(ValueError, match="max_age"):
        CachedTimeseriesSource(CountingSource(max_age=None))


@pytest.mark.parametrize("field", ["max_age", "chunk_size"])
def test_settings_reject_durations_with_years_or_months(field):
    with pytest.raises(ValidationError, match="years or months"):
        CachedTimeseriesSourceSettings.model_validate({"source": {"type": "dummy_timeseries_source"}, field: "P1M"})


def test_supported_resolutions_and_extra_args_are_forwarded():
    wrapped = DummyTimeseriesSource()
    source = CachedTimeseriesSource(wrapped, max_age=HOUR)

    assert source.supported_resolutions == wrapped.supported_resolutions
    assert source.extra_args == wrapped.extra_args


def test_create_from_settings():
    source = TimeseriesSource.create(
        {"type": "cached", "source": {"type": "dummy_timeseries_source"}, "max_age": "PT1H", "chunk_size": "PT6H"}
    )

    assert isinstance(source, CachedTimeseriesSource)
    assert isinstance(source.source, DummyTimeseriesSource)
    assert source.max_age == HOUR
    assert source.chunk_size == dt.timedelta(hours=6)


def test_settings_persist_durations_as_iso_strings():
    settings = CachedTimeseriesSourceSettings.model_validate(
        {"source": {"type": "dummy_timeseries_source"}, "max_age": "PT1H", "chunk_size": "PT6H"}
    )

    dumped = yaml.safe_load(yaml.safe_dump(settings.model_dump(round_trip=True)))

    assert (dumped["max_age"], dumped["chunk_size"]) == ("PT1H", "PT6H")
    assert CachedTimeseriesSourceSettings.model_validate(dumped) == settings


def test_settings_json_schema_describes_durations_as_strings():
    finalize()
    schema = CachedTimeseriesSourceSettings.model_json_schema(mode="validation")

    properties = schema["$defs"]["CachedTimeseriesSourceSettings"]["properties"]

    assert (properties["chunk_size"]["type"], properties["chunk_size"]["format"]) == ("string", "duration")
