import datetime as dt
import math

import pytest

from cofy.modules.simultaneity import SimultaneitySource
from cofy.modules.timeseries import TimeseriesSource

from ...timeseries.dummy_source import DummyTimeseriesSource
from ..fixed_source import QUARTER, START, FixedSource


async def fetch_values(*sources: TimeseriesSource) -> list[float]:
    result = await SimultaneitySource(list(sources)).fetch_timeseries(START, START + dt.timedelta(hours=1), QUARTER)
    return [row["value"] for row in result.to_arr()]


@pytest.mark.asyncio
async def test_ratio_of_consumption_to_production():
    consumer = FixedSource([10.0, 5.0, 20.0])
    producer = FixedSource([-10.0, -10.0, -10.0])

    assert await fetch_values(consumer, producer) == [100.0, 50.0, 200.0]


@pytest.mark.asyncio
async def test_role_follows_sign_per_timestamp():
    # a prosumer counts as production when it injects and as consumption when it takes off
    consumer = FixedSource([10.0, 10.0])
    prosumer = FixedSource([-5.0, 10.0])
    producer = FixedSource([-15.0, -10.0])

    assert await fetch_values(consumer, prosumer, producer) == [50.0, 200.0]


@pytest.mark.asyncio
async def test_no_production_is_infinite():
    values = await fetch_values(FixedSource([10.0]), FixedSource([0.0]))

    assert values == [math.inf]


@pytest.mark.asyncio
async def test_no_volume_at_all_is_balanced():
    assert await fetch_values(FixedSource([0.0]), FixedSource([0.0])) == [100.0]


@pytest.mark.asyncio
async def test_metadata_has_unit_and_earliest_expiry():
    early = dt.datetime(2026, 1, 1, 1, tzinfo=dt.UTC)
    late = dt.datetime(2026, 1, 1, 2, tzinfo=dt.UTC)
    source = SimultaneitySource(
        [
            FixedSource([10.0], metadata={"expires": late}),
            FixedSource([-10.0], metadata={"expires": early}),
            FixedSource([0.0]),
        ]
    )

    result = await source.fetch_timeseries(START, START + QUARTER, QUARTER)

    assert result.metadata == {"unit": "%", "expires": early}


def test_supported_resolutions_intersect_constrained_sources():
    source = SimultaneitySource(
        [
            FixedSource([], resolutions=["PT15M", "PT1H"]),
            FixedSource([], resolutions=["PT15M"]),
            FixedSource([]),
        ]
    )

    assert source.supported_resolutions == ["PT15M"]
    assert SimultaneitySource([FixedSource([])]).supported_resolutions == []


def test_max_age_is_the_shortest_and_unknown_if_any_is_unknown():
    hour = dt.timedelta(hours=1)
    minute = dt.timedelta(minutes=1)

    assert SimultaneitySource([FixedSource([], max_age=hour), FixedSource([], max_age=minute)]).max_age == minute
    assert SimultaneitySource([FixedSource([], max_age=hour), FixedSource([])]).max_age is None


def test_requires_a_source():
    with pytest.raises(ValueError):
        SimultaneitySource([])


def test_create_from_settings():
    source = TimeseriesSource.create(
        {
            "type": "simultaneity",
            "sources": [{"type": "dummy_timeseries_source"}, {"type": "dummy_timeseries_source"}],
        }
    )

    assert isinstance(source, SimultaneitySource)
    assert all(isinstance(child, DummyTimeseriesSource) for child in source.sources)
    assert len(source.sources) == 2
