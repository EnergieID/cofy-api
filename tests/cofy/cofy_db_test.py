from collections.abc import Sequence
from importlib import resources
from pathlib import Path

import pytest
import sqlalchemy as sa

from src.cofy.cofy_api import CofyApi
from src.cofy.db.base import Base
from src.cofy.db.cofy_db import CofyDB
from src.cofy.db.database_backed_source import DatabaseBackedSource
from tests.mocks.dummy_module import DummyModule


class DummySourcedModule(DummyModule):
    def __init__(self, name: str, migration_locations: list[str], metadata: object):
        super().__init__(name)
        self.source = DummyDbSource(migration_locations, metadata)


class DummyDbSource(DatabaseBackedSource):
    def __init__(self, migration_locations: list[str], metadata: object):
        self._migration_locations = migration_locations
        self._target_metadata = metadata

    @property
    def migration_locations(self) -> Sequence[str]:
        return self._migration_locations

    @property
    def target_metadata(self) -> object:
        return self._target_metadata


def test_db_requires_db_url():
    with pytest.raises(
        ValueError, match="CofyDB requires a database URL to be configured."
    ):
        CofyDB()


def test_db_engine_available_with_db_url():
    cofy = CofyApi(db=CofyDB(url="sqlite:///:memory:"))
    db = cofy.db
    assert db is not None
    assert db.engine is not None


def test_db_engine_is_cached():
    cofy = CofyApi(db=CofyDB(url="sqlite:///:memory:"))
    db = cofy.db
    assert db is not None
    first_engine = db.engine
    assert first_engine is db.engine


def test_migration_locations_and_target_metadata_from_sources():
    cofy = CofyApi(db=CofyDB(url="sqlite:///:memory:"))
    metadata_a = object()
    metadata_b = object()

    db_module_a = DummySourcedModule(
        name="db_a",
        migration_locations=["/tmp/migrations/a"],
        metadata=metadata_a,
    )
    db_module_b = DummySourcedModule(
        name="db_b",
        migration_locations=["/tmp/migrations/b", "/tmp/migrations/c"],
        metadata=metadata_b,
    )
    non_db_module = DummyModule("no_db")

    cofy.register_module(db_module_a)
    cofy.register_module(db_module_b)
    cofy.register_module(non_db_module)

    db = cofy.db
    assert db is not None
    assert db.migration_locations == [
        str(Path("/tmp/migrations/a").resolve()),
        str(Path("/tmp/migrations/b").resolve()),
        str(Path("/tmp/migrations/c").resolve()),
    ]
    assert db.target_metadata == [
        metadata_a,
        metadata_b,
    ]


def test_run_migrations(tmp_path: Path):
    db_file = tmp_path / "cofy_test.db"
    cofy_db = CofyDB(url=f"sqlite:///{db_file}")

    class Foo(Base):
        __tablename__ = "foo"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String, nullable=False)
        bar = sa.Column(sa.String, nullable=True)

    with resources.as_file(
        resources.files("tests.cofy.dumy_migrations")
    ) as migrations_path:
        module = DummySourcedModule(
            name="test_module",
            migration_locations=[str(migrations_path)],
            metadata=Foo.metadata,
        )
        cofy_db.register_module(module)

        cofy_db.run_migrations()

        with cofy_db.engine.connect() as connection:
            statement = sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='foo';"
            )
            result = connection.execute(statement)
            assert result.fetchone() is not None

            statement = sa.text("SELECT bar FROM foo;")
            result = connection.execute(statement)
            assert result.fetchone() is None
