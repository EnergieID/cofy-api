import datetime as dt

from pydantic import BaseModel
from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.cofy.db.base import Base
from src.cofy.db.timestamp_mixin import TimestampMixin
from src.modules.members.model import Member
from src.modules.members.models.db_member import DBMember


class DemoProduct(TimestampMixin, Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("member.id"), nullable=False)
    member: Mapped["DemoMember"] = relationship(back_populates="products")
    name: Mapped[str] = mapped_column(String, nullable=False)
    ean: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)


class DemoMember(DBMember):
    products: Mapped[list[DemoProduct]] = relationship(back_populates="member")


class DemoProductOut(BaseModel):
    ean: int
    name: str
    start_date: dt.date
    end_date: dt.date | None = None


class DemoMemberOut(Member):
    products: list[DemoProductOut]
