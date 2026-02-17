from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.cofy.cofy_api import CofyApi
from src.cofy.db.cofy_db import CofyDB
from tests.mocks.dummy_module import DummyModule


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
        assert "dummy" in self.cofy._modules
        assert "test_module" in self.cofy._modules["dummy"]
        assert self.cofy._modules["dummy"]["test_module"] is self.module
        response = self.client.get(self.module.prefix + "/hello")
        assert response.status_code == 200
        assert response.text == '"Hello from DummyModule test_module"'

    def test_tags_metadata_includes_module_tags(self):
        self.cofy.register_module(self.module)
        tags_metadata = self.cofy.tags_metadata
        type_tag = next(
            (
                tag
                for tag in tags_metadata
                if tag["name"] == self.module.type_tag["name"]
            ),
            None,
        )
        module_tag = next(
            (tag for tag in tags_metadata if tag["name"] == self.module.tag["name"]),
            None,
        )
        assert type_tag is not None
        assert module_tag is not None
        assert "x-implementations" in type_tag
        assert self.module.tag["name"] in type_tag["x-implementations"]

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
        assert "dummy" in self.cofy._modules
        assert "test_module" in self.cofy._modules["dummy"]
        assert "another_module" in self.cofy._modules["dummy"]
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
        type_tag = next(
            (tag for tag in tags if tag["name"] == self.module.type_tag["name"]),
            None,
        )
        module_tag = next(
            (tag for tag in tags if tag["name"] == self.module.tag["name"]),
            None,
        )
        assert type_tag is not None
        assert module_tag is not None

    def test_get_migration_locations_empty_for_non_db_modules(self):
        self.cofy.register_module(self.module)
        db = self.cofy.db
        assert db is not None
        assert db.migration_locations == []

    def test_get_migration_locations_for_db_modules(self):
        class DummyDbModule(DummyModule):
            uses_database = True
            migration_locations = ["/tmp/migrations/a", "/tmp/migrations/a"]

        db_module_a = DummyDbModule("db_a")
        db_module_b = DummyDbModule("db_b")
        db_module_b.migration_locations = ["/tmp/migrations/b"]

        self.cofy.register_module(db_module_a)
        self.cofy.register_module(db_module_b)

        db = self.cofy.db
        assert db is not None
        assert db.migration_locations == [
            "/tmp/migrations/a",
            "/tmp/migrations/b",
        ]

    def test_get_target_metadata_empty_for_non_db_modules(self):
        self.cofy.register_module(self.module)
        db = self.cofy.db
        assert db is not None
        assert db.target_metadata == []

    def test_get_target_metadata_for_db_modules(self):
        class DummyDbModule(DummyModule):
            uses_database = True
            target_metadata = object()

        db_module_a = DummyDbModule("db_a")
        db_module_b = DummyDbModule("db_b")
        db_module_b.target_metadata = object()

        self.cofy.register_module(db_module_a)
        self.cofy.register_module(db_module_b)

        db = self.cofy.db
        assert db is not None
        assert db.target_metadata == [
            db_module_a.target_metadata,
            db_module_b.target_metadata,
        ]

    def test_cofy_db_property_exists(self):
        assert self.cofy.db is not None


def test_cofy_db_is_optional():
    cofy = CofyApi()
    assert cofy.db is None
