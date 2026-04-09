import datetime as dt

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
    provider: TariffBreakdown | None = None
    distributor: TariffBreakdown | None = None
    fees: TariffBreakdown | None = None
    taxes: TariffBreakdown
    total: TariffBreakdown


class BillingResponse(BaseModel):
    """Response model for the billing endpoint."""

    metadata: BillingMetadata
    data: list[BillingDataPoint]
