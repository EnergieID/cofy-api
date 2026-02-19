from collections.abc import Sequence
from importlib import resources
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.cofy.db.database_backed_source import DatabaseBackedSource
from src.modules.members.models.db_member import DBMember
from src.modules.members.source import MemberSource


class MembersDbSource(MemberSource[Any], DatabaseBackedSource):
    def __init__(self, db_engine):
        self.db_engine = db_engine

    @property
    def model(self) -> Any:
        return DBMember

    def list(
        self,
        email: str | None = None,
    ) -> list[Any]:
        with Session(self.db_engine) as session:
            statement = select(self.model)
            if email is not None:
                statement = statement.where(self.model.email == email)
            return list(session.scalars(statement).all())

    def verify(self, activation_code: str) -> Any | None:
        with Session(self.db_engine) as session:
            statement = select(self.model).where(
                self.model.activation_code == activation_code
            )
            return session.scalars(statement).first()

    @property
    def migration_locations(self) -> Sequence[str]:
        with resources.as_file(
            resources.files("src.modules.members.migrations.versions")
        ) as path:
            return [str(path)]

    @property
    def target_metadata(self):
        return self.model.metadata
