from sqlmodel import Session, select

from src.modules.members.models.eb_member import EBMember
from src.modules.members.source import MemberSource


class EBDbSource(MemberSource):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    def list(self) -> list[EBMember]:
        """List all members from the database."""
        with Session(self.db_engine) as session:
            statement = select(EBMember)
            results = session.exec(statement)
            return list(results.all())
