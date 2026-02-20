import datetime as dt

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
