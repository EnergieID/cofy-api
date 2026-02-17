from collections.abc import Sequence
from pathlib import Path

from sqlalchemy.orm import joinedload
from sqlmodel import Session, SQLModel, select

from src.cofy.db.database_backed_source import DatabaseBackedSource
from src.demo.members.models import DemoMember, DemoMemberOut, DemoProduct
from src.modules.members.source import MemberSource


class DemoMembersDbSource(MemberSource[DemoMember], DatabaseBackedSource):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def list(
        self,
        email: str | None = None,
        ean: int | None = None,
    ) -> list[DemoMember]:
        with Session(self.db_engine) as session:
            statement = select(DemoMember).options(joinedload(DemoMember.products))
            if email is not None:
                statement = statement.where(DemoMember.email == email)
            if ean is not None:
                statement = statement.join(DemoProduct).where(DemoProduct.ean == ean)

            results = session.exec(statement)
            return list(results.unique().all())

    def verify(self, activation_code: str) -> DemoMember | None:
        with Session(self.db_engine) as session:
            statement = (
                select(DemoMember)
                .options(joinedload(DemoMember.products))
                .where(DemoMember.activation_code == activation_code)
            )
            return session.exec(statement).first()

    @property
    def response_model(self) -> type:
        return DemoMemberOut

    @property
    def migration_locations(self) -> Sequence[str]:
        return [str(Path(__file__).resolve().parent / "migrations" / "versions")]

    @property
    def target_metadata(self):
        return SQLModel.metadata
