import shutil
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
    db = CofyDB(url="sqlite:///:memory:")
    assert db.engine is not None


def test_db_engine_is_cached():
    db = CofyDB(url="sqlite:///:memory:")
    first_engine = db.engine
    assert first_engine is db.engine


def test_migration_locations_and_target_metadata_from_sources():
    cofy = CofyApi()
    db = CofyDB(url="sqlite:///:memory:")
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
    db.bind_api(cofy)

    assert db.migration_locations == [
        str(Path("/tmp/migrations/a").resolve()),
        str(Path("/tmp/migrations/b").resolve()),
        str(Path("/tmp/migrations/c").resolve()),
    ]
    assert db.target_metadata == [
        metadata_a,
        metadata_b,
    ]


def test_register_modules_registers_only_db_sources():
    db = CofyDB(url="sqlite:///:memory:")
    metadata = object()
    db_module = DummySourcedModule(
        name="db_module",
        migration_locations=["/tmp/migrations/db"],
        metadata=metadata,
    )
    non_db_module = DummyModule("no_db")

    db.register_modules([db_module, non_db_module])

    assert db.migration_locations == [str(Path("/tmp/migrations/db").resolve())]
    assert db.target_metadata == [metadata]


class TestDBWithMigrations:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        self.db_file = tmp_path / "cofy_test.db"
        self.cofy_db = CofyDB(url=f"sqlite:///{self.db_file}")

        with resources.as_file(
            resources.files("tests.cofy").joinpath("dumy_migrations")
        ) as migrations_path:
            self.module = DummySourcedModule(
                name="test_module",
                migration_locations=[str(migrations_path)],
                metadata=Base.metadata,
            )

            self.cofy_db.register_module(self.module)

    def test_run_migrations(self):
        self.cofy_db.run_migrations()

        with self.cofy_db.engine.connect() as connection:
            statement = sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='foo';"
            )
            result = connection.execute(statement)
            assert result.fetchone() is not None

            statement = sa.text("SELECT bar FROM foo;")
            result = connection.execute(statement)
            assert result.fetchone() is None

    def test_db_reset_empties_tables(self):
        self.cofy_db.run_migrations()

        with self.cofy_db.engine.connect() as connection:
            statement = sa.text("INSERT INTO foo (name, bar) VALUES ('test', 'value');")
            connection.execute(statement)
            connection.commit()
            statement = sa.text("SELECT bar FROM foo WHERE name='test';")
            result = connection.execute(statement)
            assert result.fetchone() == ("value",)

        self.cofy_db.reset()

        with self.cofy_db.engine.connect() as connection:
            statement = sa.text("SELECT bar FROM foo WHERE name='test';")
            result = connection.execute(statement)
            assert result.fetchone() is None

    def test_db_reset_drops_non_schema_tables(self):
        self.cofy_db.run_migrations()

        with self.cofy_db.engine.connect() as connection:
            statement = sa.text(
                "CREATE TABLE temp_table (id INTEGER PRIMARY KEY, value TEXT);"
            )
            connection.execute(statement)
            connection.commit()
            statement = sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='temp_table';"
            )
            result = connection.execute(statement)
            assert result.fetchone() is not None

        self.cofy_db.reset()

        with self.cofy_db.engine.connect() as connection:
            statement = sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='temp_table';"
            )
            result = connection.execute(statement)
            assert result.fetchone() is None


class TestGenerateMigration:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        # Copy the existing dumy_migrations to a temp directory so generated
        # files don't pollute the source tree
        src_dir = str(resources.files("tests.cofy").joinpath("dumy_migrations"))
        self.migrations_dir = tmp_path / "dumy_migrations"
        shutil.copytree(src_dir, self.migrations_dir)

        self.db_file = tmp_path / "gen_test.db"
        self.cofy_db = CofyDB(url=f"sqlite:///{self.db_file}")

        self.module = DummySourcedModule(
            name="gen_module",
            migration_locations=[str(self.migrations_dir)],
            metadata=Base.metadata,
        )
        self.cofy_db.register_module(self.module)

        # Apply the existing migrations so the branch exists in the DB
        self.cofy_db.run_migrations()

    def _generated_files(self) -> set[Path]:
        return {
            f
            for f in self.migrations_dir.iterdir()
            if f.suffix == ".py" and f.name not in ("foo.py", "bar.py")
        }

    def test_generate_migration_creates_file(self):
        assert self._generated_files() == set()

        self.cofy_db.generate_migration(
            message="add column",
            head="dummy@head",
            rev_id="baz",
            autogenerate=False,
        )

        new_files = self._generated_files()
        assert len(new_files) == 1

        new_file = new_files.pop()
        assert "baz" in new_file.name
        assert "add_column" in new_file.name

    def test_generate_migration_file_contains_correct_revision(self):
        self.cofy_db.generate_migration(
            message="second revision",
            head="dummy@head",
            rev_id="baz",
            autogenerate=False,
        )

        generated = self._generated_files().pop()
        content = generated.read_text()
        assert "revision: str = 'baz'" in content
        assert "down_revision: str | Sequence[str] | None = 'bar'" in content

    def test_generate_migration_with_autogenerate(self):
        self.cofy_db.generate_migration(
            message="auto migration",
            head="dummy@head",
            rev_id="baz",
            autogenerate=True,
        )

        generated = self._generated_files().pop()
        content = generated.read_text()
        assert "revision: str = 'baz'" in content
