from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.members.module import MembersModule
from tests.mocks.dummy_module import DummyModule


class TestModule:
    def setup_method(self):
        self.module = DummyModule("test_module")
        self.app = FastAPI()
        self.app.include_router(self.module)
        self.client = TestClient(self.app)

    def test_module_initialization(self):
        assert self.module.name == "test_module"
        assert self.module.type == "dummy"
        assert self.module.prefix == "/dummy/test_module/v1"

    def test_module_routes(self):
        response = self.client.get(self.module.prefix + "/hello")
        assert response.status_code == 200
        assert response.json() == "Hello from DummyModule test_module"

    def test_module_tag(self):
        tag = self.module.tag
        assert tag["name"] == "dummy:test_module"
        assert tag["description"] == "Dummy module for testing."
        assert tag["x-module-type"] == "dummy"
        assert tag["x-version"] == "v1"
        assert tag["x-display-name"] == "test_module"


class _DummyMemberSource:
    response_model = str

    def list(self) -> list[str]:
        return []


def test_members_module_database_contract():
    module = MembersModule(settings={"source": _DummyMemberSource()})
    assert module.uses_database is True
    assert module.target_metadata is not None
    assert module.migration_locations
    resolved = module.resolved_migration_locations
    assert len(resolved) == 1
    assert resolved[0].endswith("src/modules/members/migrations/versions")
