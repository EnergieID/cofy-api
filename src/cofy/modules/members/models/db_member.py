from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from cofy.db.base import Base
from cofy.db.timestamp_mixin import TimestampMixin


class DBMember(TimestampMixin, Base):
    __tablename__ = "member"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    activation_code: Mapped[str | None] = mapped_column(String, nullable=True, unique=True, index=True)
