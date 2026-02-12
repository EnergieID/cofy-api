import datetime as dt
from enum import StrEnum

from sqlmodel import Field, Relationship, SQLModel


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


class EBProduct(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    member_id: str = Field(foreign_key="ebmember.id")
    member: "EBMember" = Relationship(back_populates="products")
    name: str
    ean: int
    connection_type: EBConnectionType
    start_date: dt.date
    end_date: dt.date | None = None
    grid_operator: GridOperator


class EBMember(SQLModel, table=True):
    """EBMember is a member of the EnergyBar community."""

    id: str | None = Field(default=None, primary_key=True)
    email: str
    type: EBClientType
    social_tariff: bool = False
    products: list[EBProduct] = Relationship(back_populates="member")
