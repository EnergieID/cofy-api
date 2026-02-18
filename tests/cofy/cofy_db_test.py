from collections.abc import Sequence
from pathlib import Path

from src.cofy.cofy_api import CofyApi
from src.cofy.db.cofy_db import CofyDB
from src.demo.members.sources.db_source import DemoMembersDbSource
from src.modules.members.model import Member
from src.modules.members.module import MembersModule
from src.modules.members.sources.db_source import MembersDbSource
from tests.mocks.dummy_module import DummyModule


class DummyDbMemberSource:
    response_model = Member

    def __init__(self, migration_location: str, metadata: object):
        self._migration_locations = [migration_location, migration_location]
        self._target_metadata = metadata

    def list(self, email=None) -> list[Member]:
        return []

    def verify(self, activation_code: str) -> Member | None:
        return None

    @property
    def migration_locations(self) -> Sequence[str]:
        return self._migration_locations

    @property
    def target_metadata(self) -> object:
        return self._target_metadata


def test_db_engine_requires_db_url():
    cofy = CofyApi(db=CofyDB())
    db = cofy.db
    assert db is not None
    try:
        _ = db.engine
    except ValueError as exc:
        assert "No database URL configured" in str(exc)
    else:
        raise AssertionError("Expected ValueError when db_url is not configured")


def test_db_engine_available_with_db_url():
    cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
    db = cofy.db
    assert db is not None
    assert db.engine is not None


def test_db_engine_is_cached():
    cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
    db = cofy.db
    assert db is not None
    first_engine = db.engine
    assert first_engine is db.engine


def test_migration_locations_and_target_metadata_from_sources():
    cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
    metadata_a = object()
    metadata_b = object()

    db_module_a = MembersModule(
        settings={
            "name": "db_a",
            "source": DummyDbMemberSource("/tmp/migrations/a", metadata_a),
        }
    )
    db_module_b = MembersModule(
        settings={
            "name": "db_b",
            "source": DummyDbMemberSource("/tmp/migrations/b", metadata_b),
        }
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
    ]
    assert db.target_metadata == [
        metadata_a,
        metadata_b,
    ]


def test_core_and_demo_db_sources_contribute_migration_locations():
    cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
    db_module = MembersModule(
        settings={"name": "core", "source": MembersDbSource(cofy.db.engine)}
    )
    demo_module = MembersModule(
        settings={"name": "demo", "source": DemoMembersDbSource(cofy.db.engine)}
    )

    cofy.register_module(db_module)
    cofy.register_module(demo_module)

    db = cofy.db
    assert db is not None
    assert str(Path("src/modules/members/migrations/versions").resolve()) in (
        db.migration_locations
    )
    assert str(Path("src/demo/members/migrations/versions").resolve()) in (
        db.migration_locations
    )
