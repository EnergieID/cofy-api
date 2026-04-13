from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field


class CustomerType(StrEnum):
    RESIDENTIAL = "residential"
    NON_RESIDENTIAL = "non_residential"
    PROTECTED = "protected"


class ConnectionType(StrEnum):
    ELECTRICITY = "electricity"
    GAS = "gas"
    WATER = "water"


class NamedIdentifier(BaseModel):
    name: Annotated[str, Field(..., description="Human-readable name")]
    id: Annotated[str, Field(..., description="Unique identifier")]


class Contract(BaseModel):
    ean: Annotated[str, Field(..., description="European Article Number")]
    customer_type: CustomerType
    connection_type: ConnectionType
    supplier: Annotated[NamedIdentifier, Field(..., description="Energy supplier name")]
    product: Annotated[NamedIdentifier, Field(..., description="Product name")]
    distributor: Annotated[NamedIdentifier, Field(..., description="Distributor name")]
    start_date: datetime
    end_date: datetime | None
    last_invoice_date: datetime | None
    is_green: Annotated[bool, Field(..., description="Indicates if the contract guarantees green energy")]


class Address(BaseModel):
    contracts: list[Contract] = Field(default_factory=list)


class Member(BaseModel):
    id: str
    activation_code: Annotated[str | None, Field(None, description="Activation code used to verify membership")] = None
    addresses: list[Address] = Field(default_factory=list)


class VerifyMemberRequest(BaseModel):
    activation_code: str
