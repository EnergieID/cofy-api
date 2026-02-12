import datetime as dt
from enum import StrEnum

from pydantic import BaseModel

from src.modules.members.model import Member


class EBClientType(StrEnum):
    PERSONAL = "particulier"
    PROFESSIONAL = "professioneel"


class EBConnectionType(StrEnum):
    ELECTRICITY = "elektriciteit"
    GAS = "gas"


class GridOperator(StrEnum):
    IMEWO = "Fluvius Imewo"
    WEST = "Fluvius West"
    ANTWERPEN = "Fluvius Antwerpen"
    MIDDEN_VLAANDEREN = "Fluvius Midden-Vlaanderen"
    ZENNE_DIJLE = "Fluvius Zenne-Dijle"
    HALLE_VILVOORDE = "Fluvius Halle-Vilvoorde"
    KEMPEN = "Fluvius Kempen"
    LIMBURG = "Fluvius Limburg"


class EBProduct(BaseModel):
    id: int
    member_id: str
    name: str
    ean: int
    connection_type: EBConnectionType
    start_date: dt.date
    end_date: dt.date | None = None
    grid_operator: GridOperator


class EBMember(Member):
    """EBMember is a member of the EnergyBar community."""

    email: str
    type: EBClientType
    social_tariff: bool = False
    products: list[EBProduct] = []
