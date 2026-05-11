import datetime as dt

import pandas as pd
from energy_cost import Contract, Meter, MeterType, PowerDirection
from energy_cost.data import ConnectionType, CustomerType
from isodate import Duration
from pydantic import BaseModel, ConfigDict, Field, model_validator

from cofy.modules.timeseries import ISODuration


class DataPoint(BaseModel):
    timestamp: dt.datetime = Field(examples=["2024-01-01T00:00:00+01:00"])
    value: float = Field(examples=[150.5])


class MeterInfo(BaseModel):
    direction: PowerDirection = Field(default=PowerDirection.CONSUMPTION, examples=["consumption"])
    type: MeterType = Field(default=MeterType.SINGLE_RATE, examples=["single_rate"])
    data: list[DataPoint] = Field(
        min_length=2,
        examples=[
            [
                {"timestamp": "2024-01-01T00:00:00+01:00", "value": 150.5},
                {"timestamp": "2024-01-15T00:00:00+01:00", "value": 75.3},
            ]
        ],
    )

    def to_meter(self) -> Meter:
        data = pd.DataFrame(
            {
                "timestamp": [dp.timestamp for dp in self.data],
                "value": [dp.value for dp in self.data],
            }
        )
        # convert kWh to MWh for energy_cost
        data["value"] = data["value"] / 1000
        # convert iso strings to datetime
        data["timestamp"] = pd.to_datetime(data["timestamp"], format="ISO8601", utc=True)

        return Meter(
            direction=self.direction,
            type=self.type,
            data=data,
        )


class _Ref(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str


OptionalStrOrRef = str | _Ref | None


def str_or_ref_to_str(value: OptionalStrOrRef, default: str | None = None) -> str | None:
    if isinstance(value, str):
        return value
    elif isinstance(value, _Ref):
        return value.id
    else:
        return default


class ContractInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    connection_type: ConnectionType = ConnectionType.ELECTRICITY
    distributor: OptionalStrOrRef = None
    product: OptionalStrOrRef = None
    supplier: OptionalStrOrRef = None
    region: OptionalStrOrRef = None

    def to_contract(self, default_region: str = "be_flanders", default_supplier: str | None = None) -> Contract:
        return Contract(
            supplier_key=str_or_ref_to_str(self.supplier, default_supplier),
            distributor_key=str_or_ref_to_str(self.distributor),
            product_key=str_or_ref_to_str(self.product),
            region=str_or_ref_to_str(self.region, default_region),
            connection_type=self.connection_type,
            customer_type=self.customer_type,
        )


class BillingRequest(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        json_schema_extra={
            "examples": [
                {
                    "start": "2025-01-01T00:00:00+01:00",
                    "end": "2025-02-01T00:00:00+01:00",
                    "resolution": "P1M",
                    "contract": {
                        "customer_type": "residential",
                        "connection_type": "electricity",
                        "distributor": "dist1",
                        "supplier": "sup1",
                        "product": "product1",
                    },
                    "meters": [
                        {
                            "direction": "consumption",
                            "type": "single_rate",
                            "data": [
                                {"timestamp": "2025-01-01T00:00:00+01:00", "value": 150.5},
                                {"timestamp": "2025-01-01T00:15:00+01:00", "value": 75.3},
                            ],
                        }
                    ],
                }
            ]
        },
    )

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration = Field(default_factory=lambda: Duration(months=1))
    meters: list[MeterInfo] = Field(min_length=1)
    contract: ContractInfo

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "BillingRequest":
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError(f"'end' ({self.end.isoformat()}) must be after 'start' ({self.start.isoformat()}). ")
        return self
