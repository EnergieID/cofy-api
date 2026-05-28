from datetime import datetime
from enum import StrEnum
from typing import Annotated

import energy_cost as ec
from energy_cost.data import ConnectionType, CustomerType
from pydantic import BaseModel, Field


class MeterType(StrEnum):
    DAY_NIGHT_07 = "day_night_07"
    DAY_NIGHT_06 = "day_night_06"


class NamedIdentifier(BaseModel):
    name: Annotated[str, Field(..., description="Human-readable name")]
    id: Annotated[str, Field(..., description="Unique identifier")]


class Contract(BaseModel):
    ean: Annotated[str, Field(..., description="European Article Number")]
    customer_type: CustomerType
    connection_type: ConnectionType
    supplier: NamedIdentifier
    product: NamedIdentifier
    distributor: NamedIdentifier
    region: NamedIdentifier
    start_date: datetime
    end_date: datetime | None
    last_invoice_date: datetime | None
    is_green: Annotated[bool, Field(..., description="Indicates if the contract guarantees green energy")]


def _build_product_key(supplier_id: str, product_id: str, meter_type: MeterType | None = None) -> str:
    if meter_type is None:
        return product_id
    supplier = ec.Supplier.get(supplier_id)

    if supplier is not None and f"{product_id}_{meter_type.value}" in supplier.products:
        # If the supplier has a product variant for the specified meter type, use that as the product key
        return f"{product_id}_{meter_type.value}"
    return product_id


def _build_contract_history(contracts: list[Contract], meter_type: MeterType | None = None) -> list[ec.Contract]:
    return [
        ec.Contract(
            start=c.start_date,
            end=c.end_date,
            region=c.region.id,
            connection_type=c.connection_type,
            customer_type=c.customer_type,
            distributor_key=c.distributor.id,
            supplier_key=c.supplier.id,
            product_key=_build_product_key(c.supplier.id, c.product.id, meter_type),
        )
        for c in contracts
    ]


class ECContractResponse(BaseModel):
    customer_type: CustomerType
    connection_type: ConnectionType
    region: str
    distributor_key: str
    supplier_key: str | None = None
    product_key: str | None = None
    start: datetime
    end: datetime | None
    supplier: ec.Tariff | list[ec.Tariff] | None = None


class Address(BaseModel):
    contracts: list[Contract] = Field(default_factory=list)


class Member(BaseModel):
    id: str
    activation_code: Annotated[str | None, Field(None, description="Activation code used to verify membership")] = None
    addresses: list[Address] = Field(default_factory=list)

    def get_contract_history_for_ean(self, ean: str, meter_type: MeterType | None = None) -> list[ec.Contract] | None:
        contracts = [contract for address in self.addresses for contract in address.contracts if contract.ean == ean]
        if not contracts:
            return None
        return _build_contract_history(contracts, meter_type)


class VerifyMemberRequest(BaseModel):
    activation_code: str
