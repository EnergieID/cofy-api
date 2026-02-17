from src.cofy.cofy_api import CofyApi
from src.cofy.db.cofy_db import CofyDB
from tests.mocks.dummy_module import DummyModule


class DummyDbModule(DummyModule):
    uses_database = True
    migration_locations = ["/tmp/migrations/a", "/tmp/migrations/a"]
    target_metadata = object()


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


def test_migration_locations_and_target_metadata_from_modules():
    cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
    db_module_a = DummyDbModule("db_a")
    db_module_b = DummyDbModule("db_b")
    db_module_b.migration_locations = ["/tmp/migrations/b"]
    db_module_b.target_metadata = object()

    cofy.register_module(db_module_a)
    cofy.register_module(db_module_b)

    db = cofy.db
    assert db is not None
    assert db.migration_locations == [
        "/tmp/migrations/a",
        "/tmp/migrations/b",
    ]
    assert db.target_metadata == [
        db_module_a.target_metadata,
        db_module_b.target_metadata,
    ]


# def test_run_migrations_uses_bundled_alembic_runtime(monkeypatch):
#     captured: dict[str, object] = {}

#     def fake_upgrade(config, target):
#         captured["config"] = config
#         captured["target"] = target

#     cofy = CofyApi(db=CofyDB(db_url="sqlite:///:memory:"))
#     cofy.register_module(DummyDbModule("db_a"))
#     monkeypatch.setattr("src.cofy.db.cofy_db.command.upgrade", fake_upgrade)

#     cofy.db.run_migrations()

#     config = captured["config"]
#     assert captured["target"] == "heads"
#     assert config.get_main_option("sqlalchemy.url") == "sqlite:///:memory:"
#     assert config.get_main_option("script_location").endswith("src/cofy/db/alembic")
#     assert "/tmp/migrations/a" in config.get_main_option("version_locations")
