from typing import Annotated

from fastapi import Query
from sqlmodel import Session, select

from src.modules.members.models.eb_member import EBMember, EBProduct
from src.modules.members.source import MemberSource


class EBDbSource(MemberSource):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def list(
        self,
        email: Annotated[
            str | None, Query(description="Filter by email of the member")
        ] = None,
        ean: Annotated[
            int | None, Query(description="Filter by EAN of the product")
        ] = None,
    ) -> list[EBMember]:
        """List all members from the database."""
        with Session(self.db_engine) as session:
            statement = select(EBMember)
            if email is not None:
                statement = statement.where(EBMember.email == email)
            if ean is not None:
                statement = statement.join(EBProduct).where(EBProduct.ean == ean)

            results = session.exec(statement)
            return list(results.all())
