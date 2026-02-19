from collections.abc import Sequence
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.demo.members.models import DemoMember, DemoMemberOut, DemoProduct
from src.modules.members.sources.db_source import MembersDbSource


class DemoMembersDbSource(MembersDbSource):
    @property
    def model(self) -> Any:
        return DemoMember

    def list(
        self,
        email: str | None = None,
        ean: int | None = None,
    ) -> list[Any]:
        with Session(self.db_engine) as session:
            statement = select(self.model).options(joinedload(self.model.products))
            if email is not None:
                statement = statement.where(self.model.email == email)
            if ean is not None:
                statement = statement.join(DemoProduct).where(DemoProduct.ean == ean)
            return list(session.scalars(statement).unique().all())

    def verify(self, activation_code: str) -> Any | None:
        with Session(self.db_engine) as session:
            statement = (
                select(self.model)
                .options(joinedload(self.model.products))
                .where(self.model.activation_code == activation_code)
            )
            return session.scalars(statement).unique().first()

    @property
    def response_model(self) -> type:
        return DemoMemberOut

    @property
    def migration_locations(self) -> Sequence[str]:
        return list(super().migration_locations) + [
            str(Path(__file__).resolve().parent.parent / "migrations" / "versions")
        ]
