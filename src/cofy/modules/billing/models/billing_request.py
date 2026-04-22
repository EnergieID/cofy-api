import datetime as dt
from typing import Any, Literal
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

        return Meter(
            direction=self.direction,
            type=self.type,
            data=data,
        )


class BillingRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration = Field(default_factory=lambda: Duration(months=1))
    meters: list[MeterInfo] = Field(min_length=1)
    contract: Any  # narrowed to a ContractInfo subclass by make_billing_request_model

    @model_validator(mode="after")
    def end_must_be_after_start(self) -> "BillingRequest":
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError(f"'end' ({self.end.isoformat()}) must be after 'start' ({self.start.isoformat()}). ")
        return self


def make_billing_request_model(
    products: dict[str, Tariff],
    region: dict[ConnectionType, RegionalData],
) -> type[BillingRequest]:
    product_id_type = Literal[*tuple(products.keys())] | None if products else None  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]

    class _DistributorRef(BaseModel):
        model_config = ConfigDict(extra="ignore")
        id: str

    class _ProductRef(BaseModel):
        model_config = ConfigDict(extra="ignore")
        id: product_id_type  # type: ignore[valid-type]

    # Union: bare string id  OR  object with .id  OR  None
    distributor_annotation = str | _DistributorRef | None
    product_annotation = (product_id_type | _ProductRef) if products else None  # type: ignore[valid-type]

    class ContractInfo(BaseModel):
        model_config = ConfigDict(extra="ignore")
        customer_type: CustomerType = CustomerType.RESIDENTIAL
        connection_type: ConnectionType = ConnectionType.ELECTRICITY
        distributor: distributor_annotation = None  # type: ignore[valid-type]
        product: product_annotation = None  # type: ignore[valid-type]

        def to_contract(self) -> Contract:
            data = region[self.connection_type]

            distributor_id = self.distributor.id if isinstance(self.distributor, _DistributorRef) else self.distributor
            product_id = self.product.id if isinstance(self.product, _ProductRef) else self.product

            distributor_tariff = (
                data.distributors[distributor_id] if distributor_id and distributor_id in data.distributors else None
            )
            product_tariff = products[product_id] if product_id and product_id in products else None

            return Contract(
                supplier=product_tariff,
                distributor=distributor_tariff,
                fees=data.fees[self.customer_type],
                taxes=data.taxes,
                timezone=ZoneInfo("Europe/Brussels"),
            )

    first_product = next(iter(products), None)
    first_distributor = next(iter(region[ConnectionType.ELECTRICITY].distributors), None)

    _example: dict = {
        "start": "2024-01-01T00:00:00+01:00",
        "end": "2024-02-01T00:00:00+01:00",
        "resolution": "P1M",
        "contract": {
            "customer_type": "residential",
            "connection_type": "electricity",
            **(
                {
                    "distributor": first_distributor,
                }
                if first_distributor
                else {}
            ),
            **(
                {
                    "product": first_product,
                }
                if first_product
                else {}
            ),
        },
        "meters": [
            {
                "direction": "consumption",
                "type": "single_rate",
                "data": [
                    {"timestamp": "2024-01-01T00:00:00+01:00", "value": 150.5},
                    {"timestamp": "2024-01-01T00:15:00+01:00", "value": 75.3},
                ],
            }
        ],
    }

    class DynamicBillingRequest(BillingRequest):
        model_config = ConfigDict(
            arbitrary_types_allowed=True,
            json_schema_extra={"examples": [_example]},
        )
        contract: ContractInfo  # type: ignore[assignment]

    return DynamicBillingRequest
