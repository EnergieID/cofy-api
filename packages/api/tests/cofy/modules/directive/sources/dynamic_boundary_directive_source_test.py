import datetime as dt

import pandas as pd
import pytest

from cofy.modules.directive import DynamicBoundaryDirectiveSource
from cofy.modules.timeseries import ISODuration, Timeseries, TimeseriesSource

from ...timeseries.dummy_source import DummyTimeseriesSource


class DummyBoundarySource(TimeseriesSource):
    """Returns a frame with timestamp and four boundary columns b0–b3."""

    def __init__(self, boundaries: list[tuple[float, float, float, float]]):
        self._boundaries = boundaries

    async def fetch_timeseries(
        self,
        start: dt.datetime,
        end: dt.datetime,
        resolution: ISODuration = dt.timedelta(hours=1),
        **kwargs,
    ) -> Timeseries:
        data = []
        i = 0
        while start + i * resolution < end:
            b0, b1, b2, b3 = self._boundaries[i]
            data.append({"timestamp": start + i * resolution, "b0": b0, "b1": b1, "b2": b2, "b3": b3})
            i += 1
        return Timeseries(frame=pd.DataFrame(data), metadata={})


@pytest.mark.asyncio
async def test_fetch_timeseries_applies_dynamic_boundaries():
    # DummyTimeseriesSource emits values 0, 10, 20, 30, 40, 50, 60 for 7 hours
    boundary_source = DummyBoundarySource(
        boundaries=[
            (5, 15, 25, 35),  # t0: value=0  -> "--"
            (5, 15, 25, 35),  # t1: value=10 -> "-"
            (5, 15, 25, 35),  # t2: value=20 -> "0"
            (5, 15, 25, 35),  # t3: value=30 -> "+"
            (5, 15, 25, 35),  # t4: value=40 -> "++"
            (5, 15, 25, 35),  # t5: value=50 -> "++"
            (5, 15, 25, 35),  # t6: value=60 -> "++"
        ]
    )
    source = DynamicBoundaryDirectiveSource(DummyTimeseriesSource(), boundary_source)

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 7, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    assert [row["value"] for row in result.to_arr()] == ["--", "-", "0", "+", "++", "++", "++"]
    assert result.metadata["unit"] == "directive"


@pytest.mark.asyncio
async def test_fetch_timeseries_uses_per_timestamp_boundaries():
    # Boundaries shift so the same signal value maps to a different step at each timestamp
    # DummyTimeseriesSource emits value=0, 10, 20 for 3 hours
    boundary_source = DummyBoundarySource(
        boundaries=[
            (-10, 5, 15, 25),  # t0: value=0  -> "-"  (0 > -10 but not > 5)
            (-10, -5, 5, 15),  # t1: value=10 -> "+" (10 > 15? no -> "+"; 10 > 5 -> "+")
            (25, 35, 45, 55),  # t2: value=20 -> "--" (20 < 25)
        ]
    )
    source = DynamicBoundaryDirectiveSource(DummyTimeseriesSource(), boundary_source)

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    assert [row["value"] for row in result.to_arr()] == ["-", "+", "--"]


@pytest.mark.asyncio
async def test_fetch_timeseries_reversed():
    # With reverse=True, higher values map to more negative steps
    # DummyTimeseriesSource: values 0, 10, 20, 30, 40
    boundary_source = DummyBoundarySource(boundaries=[(5, 15, 25, 35)] * 5)
    source = DynamicBoundaryDirectiveSource(DummyTimeseriesSource(), boundary_source, reverse=True)

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 5, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    assert [row["value"] for row in result.to_arr()] == ["++", "+", "0", "-", "--"]


@pytest.mark.asyncio
async def test_raises_value_error_when_boundaries_are_not_ascending():
    boundary_source = DummyBoundarySource(
        boundaries=[
            (5, 15, 25, 35),  # valid
            (5, 25, 15, 35),  # b1 > b2: invalid
        ]
    )
    source = DynamicBoundaryDirectiveSource(DummyTimeseriesSource(), boundary_source)

    with pytest.raises(ValueError, match="ascending order"):
        await source.fetch_timeseries(
            dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
            dt.datetime(2026, 1, 1, 2, 0, tzinfo=dt.UTC),
            dt.timedelta(hours=1),
        )


@pytest.mark.asyncio
async def test_missing_timestamp_on_boundary_side_is_excluded():
    # If a timestamp is missing in boundary_source it should not appear in the result
    class SparseBoundarySource(TimeseriesSource):
        async def fetch_timeseries(self, start, end, resolution=dt.timedelta(hours=1), **kwargs):
            # Only returns rows for t0 and t2, skipping t1
            data = [
                {"timestamp": start, "b0": 5.0, "b1": 15.0, "b2": 25.0, "b3": 35.0},
                {"timestamp": start + 2 * resolution, "b0": 5.0, "b1": 15.0, "b2": 25.0, "b3": 35.0},
            ]
            return Timeseries(frame=pd.DataFrame(data), metadata={})

    source = DynamicBoundaryDirectiveSource(DummyTimeseriesSource(), SparseBoundarySource())

    result = await source.fetch_timeseries(
        dt.datetime(2026, 1, 1, 0, 0, tzinfo=dt.UTC),
        dt.datetime(2026, 1, 1, 3, 0, tzinfo=dt.UTC),
        dt.timedelta(hours=1),
    )

    timestamps = [row["timestamp"] for row in result.to_arr()]
    assert len(timestamps) == 2
    assert dt.datetime(2026, 1, 1, 1, 0, tzinfo=dt.UTC) not in timestamps


class ConfigurableSource(TimeseriesSource):
    def __init__(self, resolutions: list[str] | None = None, extra_args: dict | None = None):
        self._resolutions = resolutions or []
        self._extra_args = extra_args or {}

    async def fetch_timeseries(self, start, end, resolution, **kwargs):
        raise NotImplementedError

    @property
    def supported_resolutions(self):
        return self._resolutions

    @property
    def extra_args(self):
        return self._extra_args


def test_supported_resolutions_returns_intersection_of_both_sources():
    signal = ConfigurableSource(resolutions=["PT15M", "PT1H"])
    boundary = ConfigurableSource(resolutions=["PT1H", "P1D"])
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert set(source.supported_resolutions) == {"PT1H"}


def test_supported_resolutions_signal_empty_means_all_returns_boundary_list():
    signal = ConfigurableSource(resolutions=[])
    boundary = ConfigurableSource(resolutions=["PT15M", "P1D"])
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert set(source.supported_resolutions) == {"PT15M", "P1D"}


def test_supported_resolutions_boundary_empty_means_all_returns_signal_list():
    signal = ConfigurableSource(resolutions=["PT15M", "P1D"])
    boundary = ConfigurableSource(resolutions=[])
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert set(source.supported_resolutions) == {"PT15M", "P1D"}


def test_supported_resolutions_both_empty_returns_empty():
    source = DynamicBoundaryDirectiveSource(
        ConfigurableSource(resolutions=[]),
        ConfigurableSource(resolutions=[]),
    )

    assert source.supported_resolutions == []


def test_extra_args_are_union_with_signal_taking_precedence():
    signal = ConfigurableSource(extra_args={"key": str, "shared": int})
    boundary = ConfigurableSource(extra_args={"other": float, "shared": str})
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert source.extra_args == {"key": str, "other": float, "shared": int}


def test_extra_args_signal_only():
    signal = ConfigurableSource(extra_args={"a": str})
    boundary = ConfigurableSource(extra_args={})
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert source.extra_args == {"a": str}


def test_extra_args_boundary_only():
    signal = ConfigurableSource(extra_args={})
    boundary = ConfigurableSource(extra_args={"b": float})
    source = DynamicBoundaryDirectiveSource(signal, boundary)

    assert source.extra_args == {"b": float}
