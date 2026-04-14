import datetime as dt
from typing import Any, Literal
from zoneinfo import ZoneInfo

import pandas as pd
from energy_cost import Contract, Meter, MeterType, PowerDirection, Tariff
from isodate import Duration
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cofy.enums import CustomerType
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
    distributors: dict[str, Tariff],
) -> type[BillingRequest]:
    distributor_annotation = Literal[*tuple(distributors.keys())] | None if distributors else None  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]
    product_annotation = Literal[*tuple(products.keys())] | None if products else None  # type: ignore[valid-type]  # ty: ignore[invalid-type-form]

    class ContractInfo(BaseModel):
        model_config = ConfigDict(extra="ignore")
        customer_type: CustomerType = CustomerType.RESIDENTIAL
        distributor: distributor_annotation = None  # type: ignore[valid-type]
        product: product_annotation = None  # type: ignore[valid-type]

        @field_validator("distributor", "product", mode="before")
        @classmethod
        def _extract_id(cls, v: Any) -> Any:
            if isinstance(v, dict):
                return v.get("id", v)
            if hasattr(v, "id"):
                return v.id
            return v

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
                timezone=ZoneInfo("Europe/Brussels"),
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
