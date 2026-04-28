import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
from energy_cost import Contract, Meter, MeterType, PowerDirection, Tariff
from energy_cost.data import ConnectionType, CustomerType, RegionalData
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


def str_or_ref_to_str(value: OptionalStrOrRef) -> str | None:
    if isinstance(value, str):
        return value
    elif isinstance(value, _Ref):
        return value.id
    else:
        return None


class ContractInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_type: CustomerType = CustomerType.RESIDENTIAL
    connection_type: ConnectionType = ConnectionType.ELECTRICITY
    distributor: OptionalStrOrRef = None
    product: OptionalStrOrRef = None

    def to_contract(
        self,
        products: dict[ConnectionType, dict[str, Tariff]],
        region: dict[ConnectionType, RegionalData],
    ) -> Contract:
        data = region[self.connection_type]
        products_for_ct = products.get(self.connection_type, {})

        distributor = str_or_ref_to_str(self.distributor)
        product = str_or_ref_to_str(self.product)

        distributor_tariff = (
            data.distributors[distributor] if distributor and distributor in data.distributors else None
        )
        product_tariff = products_for_ct[product] if product and product in products_for_ct else None

        return Contract(
            supplier=product_tariff,
            distributor=distributor_tariff,
            fees=data.fees[self.customer_type],
            taxes=data.taxes,
            timezone=ZoneInfo("Europe/Brussels"),
        )


class BillingRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

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


def make_billing_request_model(
    products: dict[ConnectionType, dict[str, Tariff]],
    region: dict[ConnectionType, RegionalData],
) -> type[BillingRequest]:
    electricity_products = products.get(ConnectionType.ELECTRICITY, {})
    first_product = next(iter(electricity_products), None)
    electricity_region = region.get(ConnectionType.ELECTRICITY)
    first_distributor = next(iter(electricity_region.distributors), None) if electricity_region else None

    _example: dict = {
        "start": "2025-01-01T00:00:00+01:00",
        "end": "2025-02-01T00:00:00+01:00",
        "resolution": "P1M",
        "contract": {
            "customer_type": "residential",
            "connection_type": "electricity",
            **({"distributor": first_distributor} if first_distributor else {}),
            **({"product": first_product} if first_product else {}),
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

    class DynamicBillingRequest(BillingRequest):
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            json_schema_extra={"examples": [_example]},
        )

    return DynamicBillingRequest
