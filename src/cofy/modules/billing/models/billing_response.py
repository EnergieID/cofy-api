import datetime as dt

import pandas as pd
from energy_cost import CostGroup
from pydantic import BaseModel, ConfigDict

from cofy.modules.timeseries.model import ISODuration


class BillingMetadata(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration | None = None


TariffBreakdown = dict[CostGroup, dict[str, float]]


class BillingDataPoint(BaseModel):
    timestamp: dt.datetime
    supplier: TariffBreakdown | None = None
    distributor: TariffBreakdown | None = None
    fees: TariffBreakdown | None = None
    taxes: TariffBreakdown
    total: TariffBreakdown


class BillingResponse(BaseModel):
    """Response model for the billing endpoint."""

    metadata: BillingMetadata
    data: list[BillingDataPoint]

    @classmethod
    def from_df(cls, df: pd.DataFrame, metadata: BillingMetadata) -> "BillingResponse":
        """Construct a BillingResponse from a MultiIndex-column DataFrame."""
        data = []
        for _, row in df.iterrows():
            point: dict = {}
            for col, raw_value in row.items():
                value = None if pd.isna(raw_value) else raw_value
                parts = tuple(k for k in (col if isinstance(col, tuple) else (col,)) if k != "")
                d = point
                for k in parts[:-1]:
                    d = d.setdefault(k, {})
                d[str(parts[-1])] = value
            data.append(BillingDataPoint(**point))
        return cls(metadata=metadata, data=data)
