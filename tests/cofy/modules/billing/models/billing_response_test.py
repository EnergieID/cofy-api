import datetime as dt

import pandas as pd
import pytest
from energy_cost import CostGroup

from cofy.modules.billing.models.billing_response import (
    BillingDataPoint,
    BillingMetadata,
    BillingResponse,
)


def _make_cost_df(start: dt.datetime) -> pd.DataFrame:
    """Minimal MultiIndex-column DataFrame matching the output of energy_cost."""
    cols = pd.MultiIndex.from_tuples(
        [
            ("timestamp", "", ""),
            ("taxes", CostGroup.FIXED, "vat"),
            ("total", CostGroup.TOTAL, "total"),
        ]
    )
    return pd.DataFrame([[start, 0.06, 1.0]], columns=cols)


class TestBillingMetadata:
    def test_all_fields_optional_and_default_to_none(self):
        meta = BillingMetadata()
        assert meta.start is None
        assert meta.end is None
        assert meta.resolution is None

    def test_accepts_datetime_fields(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        end = dt.datetime(2024, 2, 1, tzinfo=dt.UTC)
        meta = BillingMetadata(start=start, end=end)
        assert meta.start == start
        assert meta.end == end


class TestBillingDataPoint:
    def test_creates_with_required_fields(self):
        ts = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        point = BillingDataPoint(
            timestamp=ts,
            taxes={CostGroup.FIXED: {"vat": 0.06}},
            total={CostGroup.TOTAL: {"total": 1.0}},
        )
        assert point.timestamp == ts
        assert point.provider is None
        assert point.distributor is None
        assert point.fees is None

    def test_optional_fields_accept_values(self):
        ts = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        point = BillingDataPoint(
            timestamp=ts,
            provider={CostGroup.CONSUMPTION: {"energy": 0.5}},
            distributor={CostGroup.FIXED: {"grid": 0.1}},
            fees={CostGroup.FIXED: {"levy": 0.02}},
            taxes={CostGroup.FIXED: {"vat": 0.06}},
            total={CostGroup.TOTAL: {"total": 0.68}},
        )
        assert point.provider is not None
        assert point.distributor is not None
        assert point.fees is not None


class TestBillingResponseFromDf:
    def test_returns_billing_response_instance(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        df = _make_cost_df(start)
        meta = BillingMetadata(start=start)
        result = BillingResponse.from_df(df, meta)
        assert isinstance(result, BillingResponse)

    def test_metadata_is_preserved(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        end = dt.datetime(2024, 2, 1, tzinfo=dt.UTC)
        df = _make_cost_df(start)
        meta = BillingMetadata(start=start, end=end)
        result = BillingResponse.from_df(df, meta)
        assert result.metadata.start == start
        assert result.metadata.end == end

    def test_data_length_matches_dataframe_rows(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        end = dt.datetime(2024, 2, 1, tzinfo=dt.UTC)
        cols = pd.MultiIndex.from_tuples(
            [
                ("timestamp", "", ""),
                ("taxes", CostGroup.FIXED, "vat"),
                ("total", CostGroup.TOTAL, "total"),
            ]
        )
        df = pd.DataFrame(
            [
                [start, 0.06, 1.0],
                [end, 0.06, 1.0],
            ],
            columns=cols,
        )
        result = BillingResponse.from_df(df, BillingMetadata())
        assert len(result.data) == 2

    def test_timestamp_is_parsed_correctly(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        df = _make_cost_df(start)
        result = BillingResponse.from_df(df, BillingMetadata())
        assert result.data[0].timestamp == start

    def test_absent_optional_fields_remain_none(self):
        """Columns for optional fields absent from the DataFrame should stay None."""
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        df = _make_cost_df(start)
        result = BillingResponse.from_df(df, BillingMetadata())
        point = result.data[0]
        assert point.provider is None
        assert point.distributor is None
        assert point.fees is None

    def test_nested_structure_matches_multiindex(self):
        start = dt.datetime(2024, 1, 1, tzinfo=dt.UTC)
        df = _make_cost_df(start)
        result = BillingResponse.from_df(df, BillingMetadata())
        point = result.data[0]
        assert CostGroup.FIXED in point.taxes
        assert "vat" in point.taxes[CostGroup.FIXED]
        assert point.taxes[CostGroup.FIXED]["vat"] == pytest.approx(0.06)
