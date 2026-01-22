from fastapi.testclient import TestClient

from src.cofy.app import Cofy
from tests.cofy.dummy_module import DummyModule


class TestApi:
    def setup_method(self):
        self.cofy = Cofy(settings={})
        self.module = DummyModule(
            name="testmodule", type_="testtype", router=None, metadata={"info": "test"}
        )
        self.cofy.register_module(self.module)
        self.client = TestClient(self.cofy.fastApi)

    def test_get_modules(self):
        response = self.client.get("/v1/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(mt["module_type"] == "testtype" for mt in data)
        # Check that our module is present
        found = False
        for mt in data:
            if mt["module_type"] == "testtype":
                for mod in mt["modules"]:
                    if mod["module_name"] == "testmodule":
                        found = True
        assert found

    def test_get_modules_by_type(self):
        response = self.client.get("/v1/testtype")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(mod["module_name"] == "testmodule" for mod in data)

    def test_get_module(self):
        response = self.client.get("/v1/testtype/testmodule")
        assert response.status_code == 200
        data = response.json()
        assert data["module_type"] == "testtype"
        assert data["module_name"] == "testmodule"
        assert data["metadata"] == {"info": "test"}

    def test_get_module_not_found(self):
        response = self.client.get("/v1/testtype/doesnotexist")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
