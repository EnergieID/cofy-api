from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy import CofyAPI
from cofy.api.token_auth import TokenAuth, TokenInfo
from tests.mocks.dummy_module import DummyModule


def test_cofy_initialization():
    cofy = CofyAPI(title="Test API", version="1.2.3", description="Test desc")
    assert isinstance(cofy, FastAPI)
    assert cofy.title == "Test API"
    assert cofy.version == "1.2.3"
    assert cofy.description == "Test desc"


def test_debug_mode_registers_debug_routes(tmp_path):
    """CofyAPI with debug_mode=True must register the /debug/* endpoints."""
    cofy = CofyAPI(debug_mode=True, debug_dir=tmp_path)
    route_paths = [r.path for r in cofy.routes if hasattr(r, "path")]
    assert any("/debug/" in str(p) for p in route_paths)


def test_debug_mode_uses_tempdir_when_no_dir_given():
    """CofyAPI with debug_mode=True and no debug_dir must not raise."""
    cofy = CofyAPI(debug_mode=True)
    client = TestClient(cofy)
    response = client.get("/health")
    assert response.status_code == 200


def test_debug_mode_adds_profiling_headers(tmp_path):
    """Requests through a debug-enabled CofyAPI must carry profiling headers."""
    cofy = CofyAPI(debug_mode=True, debug_dir=tmp_path)
    client = TestClient(cofy)
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Debug-Id" in response.headers
    assert "X-Debug-Url" in response.headers


def test_constructor_registers_provided_modules():
    module = DummyModule("test_module")
    cofy = CofyAPI(modules=[module])
    client = TestClient(cofy)

    assert cofy.modules == (module,)
    response = client.get(f"{module.prefix}/hello")
    assert response.status_code == 200
    assert response.text == '"Hello from DummyModule test_module"'


def test_creation_from_settings():
    settings = {
        "type": "cofy_api",
        "debug_mode": True,
        "modules": [
            {
                "type": "dummy",
                "name": "foo",
                "description": "bar",
            }
        ],
    }
    cofy = CofyAPI.create(settings)
    assert isinstance(cofy, CofyAPI)
    assert len(cofy.modules) == 1
    assert isinstance(cofy.modules[0], DummyModule)
    assert cofy.modules[0].name == "foo"


def test_auth_adds_dependency_when_no_dependencies_provided():
    cofy = CofyAPI(auth=TokenAuth({"token": TokenInfo(name="Demo")}))
    client = TestClient(cofy)

    response = client.get("/health", params={"token": "token"})

    assert response.status_code == 200


def test_auth_appends_dependency_when_dependencies_already_provided():
    cofy = CofyAPI(
        auth=TokenAuth({"token": TokenInfo(name="Demo")}),
        dependencies=[],
    )
    client = TestClient(cofy)

    response = client.get("/health", params={"token": "token"})

    assert response.status_code == 200


class TestCofyAPIModuleRegistration:
    def setup_method(self):
        self.cofy = CofyAPI()
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

    def test_health_check_endpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_root_path_updates_paths_in_openapi(self):
        parent = FastAPI()
        cofy = CofyAPI(root_path="/api/v1")
        parent.mount("/api/v1", cofy)
        cofy.register_module(self.module)
        client = TestClient(parent)
        response = client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        data = response.json()
        # Paths are relative per the OpenAPI spec; the mount prefix appears in servers.
        assert f"{self.module.prefix}/hello" in data["paths"]
        servers = [s["url"] for s in data.get("servers", [])]
        assert "/api/v1" in servers

        response = client.get(f"/api/v1{self.module.prefix}/hello")
        assert response.status_code == 200
        assert response.text == '"Hello from DummyModule test_module"'
