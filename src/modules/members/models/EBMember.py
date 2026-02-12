import datetime as dt
from enum import StrEnum

from pydantic import BaseModel

from src.modules.members.model import Member


class EBClientType(StrEnum):
    PERSONAL = "personal"
    PROFESSIONAL = "professional"


class EBConnectionType(StrEnum):
    ELECTRICITY = "electricity"
    GAS = "gas"


class EBProduct(BaseModel):
    member_id: int
    product_name: str
    ean: int
    connection_type: EBConnectionType
    start_date: dt.date
    end_date: dt.date | None = None


class EBMember(Member):
    """EBMember is a member of the EnergyBar community."""

    email: str
    client_number: str
    client_type: EBClientType
    social_tariff: bool = False
    products: list[EBProduct] = []
