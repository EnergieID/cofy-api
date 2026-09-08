from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.mocks.dummy_module import DummyModule


class TestModule:
    def setup_method(self):
        self.module = DummyModule("test_module")
        self.module.add_api_route(
            "/custom",
            lambda: "Custom operation",
            methods=["GET"],
            operation_id="customOp",
        )
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

    def test_operation_id_in_openapi(self):
        openapi = self.client.get("/openapi.json").json()
        # Find the operationId for /dummy/test_module/v1/hello
        op_id = openapi["paths"]["/dummy/test_module/v1/hello"]["get"]["operationId"]
        assert op_id == "dummy:test_module:hello"
        # Find the operationId for /dummy/test_module/v1/custom
        op_id_custom = openapi["paths"]["/dummy/test_module/v1/custom"]["get"]["operationId"]
        assert op_id_custom == "dummy:test_module:customOp"
