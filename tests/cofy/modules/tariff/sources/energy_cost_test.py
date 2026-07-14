import datetime as dt
from unittest.mock import MagicMock

import pandas as pd
import pytest
from energy_cost import CostGroup
from isodate import Duration

from cofy.modules.tariff.sources.energy_cost import EnergyCostTariffSource


@pytest.mark.asyncio
async def test_fetch_timeseries():
    mock_tariff = MagicMock()
    src = EnergyCostTariffSource(mock_tariff)
    start = dt.datetime(2026, 1, 1, tzinfo=dt.UTC)
    end = dt.datetime(2026, 1, 2, tzinfo=dt.UTC)
    resolution = dt.timedelta(hours=1)

    mock_tariff.get_values.return_value = pd.DataFrame(
        {
            "timestamp": [start, start + resolution],
            "total": [10.0, 20.0],
        }
    )

    result = await src.fetch_timeseries(start, end, resolution=resolution, cost_group=CostGroup.CONSUMPTION)

    assert result.metadata["unit"] == "EUR/MWh"
    assert len(result.frame) == 2
    mock_tariff.get_values.assert_called_once_with(
        start=start,
        end=end,
        output_resolution=resolution,
        cost_group=CostGroup.CONSUMPTION,
    )


@pytest.mark.asyncio
async def test_fetch_timeseries_raises_for_duration():
    src = EnergyCostTariffSource(MagicMock())
    with pytest.raises(ValueError, match="Resolution only support time components"):
        await src.fetch_timeseries(
            dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            dt.datetime(2026, 2, 1, tzinfo=dt.UTC),
            resolution=Duration(months=1),
        )


@pytest.mark.asyncio
async def test_fetch_timeseries_raises_for_missing_cost_group():
    src = EnergyCostTariffSource(MagicMock())
    with pytest.raises(ValueError, match="Cost group must be provided."):
        await src.fetch_timeseries(
            dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
            resolution=dt.timedelta(hours=1),
        )


@pytest.mark.asyncio
async def test_fetch_timeseries_raises_when_series_is_none():
    mock_tariff = MagicMock()
    src = EnergyCostTariffSource(mock_tariff)
    mock_tariff.get_values.return_value = None
    with pytest.raises(ValueError, match="No tariff data available"):
        await src.fetch_timeseries(
            dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
            dt.datetime(2026, 1, 2, tzinfo=dt.UTC),
            resolution=dt.timedelta(hours=1),
            cost_group=CostGroup.CONSUMPTION,
        )


def test_supported_resolutions():
    src = EnergyCostTariffSource(MagicMock())
    assert src.supported_resolutions == ["PT5M", "PT15M", "PT1H", "P1D", "P7D"]


def test_extra_args():
    src = EnergyCostTariffSource(MagicMock())
    args = src.extra_args
    assert "cost_group" in args
