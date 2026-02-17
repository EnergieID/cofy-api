import datetime as dt

from pydantic import BaseModel
from sqlalchemy.orm import Mapped
from sqlmodel import Field, Relationship, SQLModel

from src.cofy.db.timestamp_mixin import TimestampMixin
from src.modules.members.model import Member


class DemoProduct(TimestampMixin, SQLModel, table=True):
    __tablename__ = "product"
    id: int | None = Field(default=None, primary_key=True)
    member_id: str = Field(foreign_key="member.id")
    member: Mapped["DemoMember"] = Relationship(back_populates="products")
    name: str
    ean: int
    start_date: dt.date
    end_date: dt.date | None = None


class DemoMember(TimestampMixin, SQLModel, table=True):
    __tablename__ = "member"
    id: str | None = Field(default=None, primary_key=True)
    email: str
    activation_code: str = Field(index=True, unique=True)
    products: Mapped[list[DemoProduct]] = Relationship(back_populates="member")


class DemoProductOut(BaseModel):
    ean: int
    name: str
    start_date: dt.date
    end_date: dt.date | None = None


class DemoMemberOut(Member):
    products: list[DemoProductOut]
