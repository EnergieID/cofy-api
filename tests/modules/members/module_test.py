import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.modules.members.model import Member
from src.modules.members.module import MembersModule


class DummyMemberSource:
    response_model = Member

    def __init__(self):
        self.activation_codes = {
            "code-a": "1",
            "code-b": "2",
        }
        self.members = [
            Member(id="1", email="a@example.com"),
            Member(id="2", email="b@example.com"),
        ]

    def list(self, email=None) -> list[Member]:
        members = self.members
        if email is not None:
            members = [member for member in members if member.email == email]
        return members

    def verify(self, activation_code: str) -> Member | None:
        member_id = self.activation_codes.get(activation_code)
        if member_id is None:
            return None
        return next((member for member in self.members if member.id == member_id), None)


def test_members_module_list_and_verify_routes():
    app = FastAPI()
    module = MembersModule(settings={"source": DummyMemberSource(), "name": "dummy"})
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix, params={"email": "a@example.com"})
    assert response.status_code == 200
    assert len(response.json()) == 1

    response = client.post(
        module.prefix + "/verify", json={"activation_code": "code-a"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == "1"

    response = client.post(
        module.prefix + "/verify", json={"activation_code": "invalid"}
    )
    assert response.status_code == 404


def test_removed_activation_get_endpoints_return_404():
    app = FastAPI()
    module = MembersModule(settings={"source": DummyMemberSource(), "name": "dummy"})
    app.include_router(module)
    client = TestClient(app)

    response = client.get(module.prefix + "/activation/code-a")
    assert response.status_code == 404

    response = client.get(module.prefix + "/activation/code-a/validate")
    assert response.status_code == 404


def test_source_is_required_for_members_module():
    with pytest.raises(ValueError):
        MembersModule(settings={"name": "dummy"})
