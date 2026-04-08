import datetime as dt
from enum import StrEnum

import pandas as pd
from energy_cost import Contract, Meter, MeterType, PowerDirection, Tariff
from isodate import Duration
from pydantic import BaseModel

from cofy.modules.timeseries import ISODuration


class DataPoint(BaseModel):
    """Data point for cost calculation."""

    timestamp: dt.datetime
    value: float


class MeterInfo(BaseModel):
    """Information about the meter for cost calculation."""

    direction: PowerDirection = PowerDirection.CONSUMPTION
    type: MeterType = MeterType.SINGLE_RATE
    data: list[DataPoint]

    def to_meter(self) -> Meter:
        """Convert MeterInfo to a Meter object."""
        return Meter(
            direction=self.direction,
            type=self.type,
            data=pd.DataFrame(
                {
                    "timestamp": [dp.timestamp for dp in self.data],
                    "value": [dp.value for dp in self.data],
                }
            ),
        )


class CustomerType(StrEnum):
    RESIDENTIAL = "residential"
    NON_RESIDENTIAL = "non_residential"
    PROTECTED = "protected"


class ContractInfo(BaseModel):
    """Information about the contract for cost calculation."""

    customer_type: CustomerType = CustomerType.RESIDENTIAL
    distributor: str | None = None
    product: str | None = None

    def to_contract(self, products: dict[str, Tariff]) -> Contract:
        """Convert ContractInfo to a Contract object."""
        from energy_cost.data.be import distributors, fees, tax_rate

        tariffs = {
            "belgian_fees": fees[f"be_{self.customer_type.value}"],
            "flemish_fees": fees[f"be_flemish_{self.customer_type.value}"],
        }
        if self.distributor and self.distributor in distributors:
            tariffs["distributor"] = distributors[self.distributor]
        if self.product and self.product in products:
            tariffs["providor"] = products[self.product]

        return Contract(tax_rate=tax_rate, tariffs=tariffs)


class BillingRequest(BaseModel):
    """Request model for cost calculation."""

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration = Duration(months=1)
    meters: list[MeterInfo]
    contract: ContractInfo
