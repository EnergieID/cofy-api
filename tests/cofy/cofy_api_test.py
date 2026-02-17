from collections.abc import Sequence
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.cofy.cofy_api import CofyApi
from src.cofy.db.cofy_db import CofyDB
from src.modules.members.model import Member
from src.modules.members.module import MembersModule
from tests.mocks.dummy_module import DummyModule


class DummyDbMemberSource:
    response_model = Member

    def __init__(self, migration_location: str, metadata: object):
        self._migration_locations = [migration_location, migration_location]
        self._target_metadata = metadata

    def list(self, email=None, **filters) -> list[Member]:
        return []

    def verify(self, activation_code: str) -> Member | None:
        return None

    @property
    def migration_locations(self) -> Sequence[str]:
        return self._migration_locations

    @property
    def target_metadata(self) -> object:
        return self._target_metadata


def test_cofy_initialization():
    cofy = CofyApi(title="Test API", version="1.2.3", description="Test desc")
    assert isinstance(cofy, FastAPI)
    assert cofy.title == "Test API"
    assert cofy.version == "1.2.3"
    assert cofy.description == "Test desc"


class TestCofyApiModuleRegistration:
    def setup_method(self):
        self.cofy = CofyApi(db=CofyDB())
        self.module = DummyModule("test_module")
        self.client = TestClient(self.cofy)

    def test_register_module(self):
        self.cofy.register_module(self.module)
        assert self.module in self.cofy._modules
        response = self.client.get(self.module.prefix + "/hello")
        assert response.status_code == 200
        assert response.text == '"Hello from DummyModule test_module"'

    def test_tags_metadata_includes_module_tags(self):
        self.cofy.register_module(self.module)
        tags_metadata = self.cofy.tags_metadata
        module_tag = next(
            (tag for tag in tags_metadata if tag["name"] == self.module.tag["name"]),
            None,
        )
        assert module_tag is not None
        assert "x-module-type" in module_tag
        assert module_tag["x-module-type"] == self.module.type
        assert "x-version" in module_tag
        assert module_tag["x-version"] == self.module.version
        assert "x-display-name" in module_tag
        assert module_tag["x-display-name"] == self.module.name

    def test_openapi_includes_module_routes(self):
        self.cofy.register_module(self.module)
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert self.module.prefix + "/hello" in data["paths"]

    def test_multiple_modules_registration(self):
        module2 = DummyModule("another_module")
        self.cofy.register_module(self.module)
        self.cofy.register_module(module2)
        assert self.module in self.cofy._modules
        assert module2 in self.cofy._modules
        response1 = self.client.get(self.module.prefix + "/hello")
        response2 = self.client.get(module2.prefix + "/hello")
        assert response1.status_code == 200
        assert response1.text == '"Hello from DummyModule test_module"'
        assert response2.status_code == 200
        assert response2.text == '"Hello from DummyModule another_module"'

    def test_open_api_includes_tags_metadata(self):
        self.cofy.register_module(self.module)
        response = self.client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        tags = data.get("tags", [])
        module_tag = next(
            (tag for tag in tags if tag["name"] == self.module.tag["name"]),
            None,
        )
        assert module_tag is not None

    def test_get_migration_locations_empty_for_non_db_sources(self):
        self.cofy.register_module(self.module)
        db = self.cofy.db
        assert db is not None
        assert db.migration_locations == []

    def test_get_migration_locations_for_db_sources(self):
        db_module_a = MembersModule(
            settings={
                "name": "db_a",
                "source": DummyDbMemberSource("/tmp/migrations/a", object()),
            }
        )
        db_module_b = MembersModule(
            settings={
                "name": "db_b",
                "source": DummyDbMemberSource("/tmp/migrations/b", object()),
            }
        )

        self.cofy.register_module(db_module_a)
        self.cofy.register_module(db_module_b)

        db = self.cofy.db
        assert db is not None
        assert db.migration_locations == [
            str(Path("/tmp/migrations/a").resolve()),
            str(Path("/tmp/migrations/b").resolve()),
        ]

    def test_get_target_metadata_empty_for_non_db_sources(self):
        self.cofy.register_module(self.module)
        db = self.cofy.db
        assert db is not None
        assert db.target_metadata == []

    def test_get_target_metadata_for_db_sources(self):
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

        self.cofy.register_module(db_module_a)
        self.cofy.register_module(db_module_b)

        db = self.cofy.db
        assert db is not None
        assert db.target_metadata == [metadata_a, metadata_b]

    def test_cofy_db_property_exists(self):
        assert self.cofy.db is not None


def test_cofy_db_is_optional():
    cofy = CofyApi()
    try:
        _ = cofy.db
    except AssertionError as exc:
        assert "CofyDB instance is not configured" in str(exc)
    else:
        raise AssertionError("Expected an assertion when db is not configured")
