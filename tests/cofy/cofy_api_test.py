from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.cofy_api import CofyApi
from tests.mocks.dummy_module import DummyModule


def test_cofy_initialization():
    cofy = CofyApi(title="Test API", version="1.2.3", description="Test desc")
    assert isinstance(cofy, FastAPI)
    assert cofy.title == "Test API"
    assert cofy.version == "1.2.3"
    assert cofy.description == "Test desc"


class TestCofyApiModuleRegistration:
    def setup_method(self):
        self.cofy = CofyApi()
        self.module = DummyModule("test_module")
        self.client = TestClient(self.cofy)

    def test_register_module(self):
        self.cofy.register_module(self.module)
        assert self.module in self.cofy.modules
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
        assert self.module in self.cofy.modules
        assert module2 in self.cofy.modules
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
