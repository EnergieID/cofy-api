import datetime as dt
from enum import StrEnum
from typing import Any, Literal

import pandas as pd
from energy_cost import Contract, Meter, MeterType, PowerDirection, Tariff
from isodate import Duration
from pydantic import BaseModel, ConfigDict, Field

from cofy.modules.timeseries import ISODuration


class DataPoint(BaseModel):
    timestamp: dt.datetime = Field(examples=["2024-01-01T00:00:00+01:00"])
    value: float = Field(examples=[150.5])


class MeterInfo(BaseModel):
    direction: PowerDirection = Field(default=PowerDirection.CONSUMPTION, examples=["consumption"])
    type: MeterType = Field(default=MeterType.SINGLE_RATE, examples=["single_rate"])
    data: list[DataPoint] = Field(
        examples=[
            [
                {"timestamp": "2024-01-01T00:00:00+01:00", "value": 150.5},
                {"timestamp": "2024-01-15T00:00:00+01:00", "value": 75.3},
            ]
        ]
    )

    def to_meter(self) -> Meter:
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


class BillingRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    start: dt.datetime | None = None
    end: dt.datetime | None = None
    resolution: ISODuration = Field(default_factory=lambda: Duration(months=1))
    meters: list[MeterInfo]
    contract: Any  # narrowed to a ContractInfo subclass by make_billing_request_model


def make_billing_request_model(
    products: dict[str, Tariff],
    distributors: dict[str, Tariff],
) -> type[BillingRequest]:
    distributor_annotation = Literal[*tuple(distributors.keys())] | None if distributors else None  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]
    product_annotation = Literal[*tuple(products.keys())] | None if products else None  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]

    class ContractInfo(BaseModel):
        customer_type: CustomerType = CustomerType.RESIDENTIAL
        distributor: distributor_annotation = None  # type: ignore[valid-type]
        product: product_annotation = None  # type: ignore[valid-type]

        def to_contract(self) -> Contract:
            from energy_cost.data.be import fees, tax_rate

            fee_tariffs = [
                fees[f"be_{self.customer_type.value}"],
                fees[f"flanders_{self.customer_type.value}"],
            ]
            distributor_tariff = (
                distributors[self.distributor] if self.distributor and self.distributor in distributors else None
            )
            product_tariff = products[self.product] if self.product and self.product in products else None

            return Contract(
                provider=product_tariff,
                distributor=distributor_tariff,
                fees=fee_tariffs,
                tax_rate=tax_rate,
            )

    first_product = next(iter(products), None)
    first_distributor = next(iter(distributors), None)

    _example: dict = {
        "start": "2024-01-01T00:00:00+01:00",
        "end": "2024-02-01T00:00:00+01:00",
        "resolution": "P1M",
        "contract": {
            "customer_type": "residential",
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
