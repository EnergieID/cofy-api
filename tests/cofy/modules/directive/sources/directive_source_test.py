import datetime as dt

import pytest

from cofy.modules.directive import DirectiveSource

from ...timeseries.dummy_source import DummyTimeseriesSource


@pytest.mark.asyncio
async def test_fetch_timeseries_maps_values_to_directive_steps():
    source = DirectiveSource(
        DummyTimeseriesSource(),
        boundaries=(0, 10, 20, 40),
    )

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 7, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    assert [row["value"] for row in result.to_arr()] == ["--", "-", "0", "+", "+", "++", "++"]
    assert result.metadata["unit"] == "directive"


@pytest.mark.asyncio
async def test_fetch_timeseries_maps_values_to_reversed_directive_steps():
    source = DirectiveSource(
        DummyTimeseriesSource(),
        boundaries=(0, 10, 20, 30),
        reverse=True,
    )

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 5, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    assert [row["value"] for row in result.to_arr()] == ["++", "+", "0", "-", "--"]


def test_supported_resolutions_and_extra_args_are_forwarded():
    wrapped = DummyTimeseriesSource()
    source = DirectiveSource(wrapped, boundaries=(5, 15, 25, 35))

    assert source.supported_resolutions == wrapped.supported_resolutions
    assert source.extra_args == wrapped.extra_args
