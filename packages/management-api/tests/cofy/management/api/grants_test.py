"""Integration tests for GrantsRouter, with the grants kept in the users file."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.grants import GrantsRouter
from cofy.management.auth.access import Role
from cofy.management.auth.session import install_session
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.communities import FileCommunitiesPersistence
from cofy.management.persitance.file.grants import FileGrantsPersistence

from ..access_fixture import ISSUER, OIDC_CONFIG, log_in, log_in_as_system_admin, user

GRANTS = "/management/communities/test/grants"
ANN = {"email": "ann@example.com", "issuer": ISSUER, "subject": "ann-sub", "grants": {"test": "community_admin"}}


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    (tmp_path / "test.yaml").write_text(yaml.safe_dump({"type": "cofy_api"}))
    (tmp_path / "other.yaml").write_text(yaml.safe_dump({"type": "cofy_api"}))
    (tmp_path / "access").mkdir()
    (tmp_path / "access" / "users.yaml").write_text(yaml.safe_dump({"users": [ANN]}))
    return tmp_path


def app_for(tmp_data: Path) -> FastAPI:
    app = FastAPI()
    add_exception_handlers(app)
    grants = FileGrantsPersistence(tmp_data / "access" / "users.yaml")
    app.include_router(GrantsRouter(grants, FileCommunitiesPersistence(tmp_data)).router)
    return app


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    app = app_for(tmp_data)
    log_in_as_system_admin(app)
    return TestClient(app, raise_server_exceptions=False)


def stored(tmp_data: Path) -> list[dict]:
    return yaml.safe_load((tmp_data / "access" / "users.yaml").read_text())["users"]


def test_lists_the_grants(client: TestClient):
    assert client.get(GRANTS).json() == [{"email": "ann@example.com", "role": "community_admin", "bound": True}]


def test_granting_a_role_to_someone_new_adds_them_unbound(client: TestClient, tmp_data: Path):
    r = client.post(GRANTS, json={"email": "bob@example.com", "role": "community_admin"})

    assert r.status_code == 201
    assert r.json() == {"email": "bob@example.com", "role": "community_admin", "bound": False}
    assert stored(tmp_data)[1] == {"email": "bob@example.com", "grants": {"test": "community_admin"}}


def test_granting_a_role_in_another_community_adds_it_to_the_same_person(client: TestClient, tmp_data: Path):
    client.post("/management/communities/other/grants", json={"email": "ANN@example.com", "role": "community_admin"})

    assert stored(tmp_data) == [ANN | {"grants": {"test": "community_admin", "other": "community_admin"}}]


def test_a_person_can_only_have_one_role_in_a_community(client: TestClient):
    assert client.post(GRANTS, json={"email": "ANN@example.com", "role": "community_admin"}).status_code == 409


def test_a_grant_needs_a_valid_email(client: TestClient):
    assert client.post(GRANTS, json={"email": "not-an-email", "role": "community_admin"}).status_code == 422


def test_a_client_cannot_bind_a_grant(client: TestClient, tmp_data: Path):
    client.post(GRANTS, json={"email": "bob@example.com", "role": "community_admin", "subject": "forged"})

    assert "subject" not in stored(tmp_data)[1]


def test_changing_a_role_keeps_the_binding(client: TestClient, tmp_data: Path):
    r = client.put(f"{GRANTS}/ann@example.com", json={"email": "ann@example.com", "role": "community_admin"})

    assert r.status_code == 200
    assert stored(tmp_data) == [ANN]


def test_changing_cannot_move_a_grant_to_someone_else(client: TestClient):
    r = client.put(f"{GRANTS}/ann@example.com", json={"email": "eve@example.com", "role": "community_admin"})

    assert r.status_code == 422


def test_revoking_someones_last_role_forgets_them(client: TestClient, tmp_data: Path):
    assert client.delete(f"{GRANTS}/ann@example.com").status_code == 204
    assert stored(tmp_data) == []


def test_an_unknown_grant_returns_404(client: TestClient):
    assert client.get(f"{GRANTS}/nobody@example.com").status_code == 404


def test_grants_in_a_community_that_does_not_exist_return_404(client: TestClient):
    assert client.get("/management/communities/missing/grants").status_code == 404
    r = client.post(
        "/management/communities/missing/grants", json={"email": "bob@example.com", "role": "community_admin"}
    )
    assert r.status_code == 404


# ── who may manage grants ─────────────────────────────────────────────────


def test_a_community_admin_manages_their_own_communitys_grants(tmp_data: Path):
    app = app_for(tmp_data)
    log_in(app, user("ann", grants={"test": Role.community_admin}))
    client = TestClient(app)

    assert client.post(GRANTS, json={"email": "bob@example.com", "role": "community_admin"}).status_code == 201
    assert client.get("/management/communities/other/grants").status_code == 403


def test_grants_are_not_reachable_without_a_login(tmp_data: Path):
    app = app_for(tmp_data)
    install_session(app, OIDC_CONFIG)

    r = TestClient(app, raise_server_exceptions=False).get(GRANTS)

    assert r.status_code == 401
    assert r.json()["code"] == "not-authenticated"
