import builtins

from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.modules.members import Member, MembersModule, MemberSource


class DummyMemberSource(MemberSource[Member]):
    response_model = Member

    def __init__(self):
        self.activation_codes = {
            "code-a": "1",
            "code-b": "2",
        }
        self.members = [
            Member(id="1"),
            Member(id="2"),
        ]

    def list(self, email: str | None = None) -> builtins.list[Member]:
        return self.members

    def get(self, member_id: str) -> Member | None:
        return next((m for m in self.members if m.id == member_id), None)

    def verify(self, activation_code: str) -> Member | None:
        member_id = self.activation_codes.get(activation_code)
        if member_id is None:
            return None
        return next((member for member in self.members if member.id == member_id), None)


def test_members_module_list_and_verify_routes():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix)
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.post(module.prefix + "/verify", json={"activation_code": "code-a"})
    assert response.status_code == 200
    assert response.json()["id"] == "1"

    response = client.post(module.prefix + "/verify", json={"activation_code": "invalid"})
    assert response.status_code == 404


def test_members_module_get_by_id():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix + "/1")
    assert response.status_code == 200
    assert response.json()["id"] == "1"

    response = client.get(module.prefix + "/nonexistent")
    assert response.status_code == 404


def test_removed_activation_get_endpoints_return_404():
    app = FastAPI()
    module = MembersModule(source=DummyMemberSource(), name="dummy")
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix + "/activation/code-a")
    assert response.status_code == 404

    response = client.get(module.prefix + "/activation/code-a/validate")
    assert response.status_code == 404
