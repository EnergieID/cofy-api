"""Integration tests for TokensRouter: keys are generated, shown once and stored only as a hash."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cofy.api import CofyAPI, hash_key
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.tokens import TokensRouter
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.tokens import FileTokensPersistence

from ..access_fixture import log_in_as_system_admin

TOKENS = "/management/communities/test/tokens"


def write_community(path: Path, auth: dict | None) -> None:
    community = {"type": "cofy_api", "modules": [{"type": "billing", "name": "default"}]}
    if auth is not None:
        community["auth"] = auth
    (path / "test.yaml").write_text(yaml.safe_dump(community))


def stored(path: Path) -> dict:
    return yaml.safe_load((path / "test.yaml").read_text())


def stored_token(path: Path, name: str) -> dict:
    return next(token for token in stored(path)["auth"]["tokens"] if token["name"] == name)


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    """A token set up by hand as a plain key, and one as a hash."""
    write_community(
        tmp_path,
        {
            "type": "token",
            "tokens": [
                {"name": "plain", "description": "By hand", "key": "plain-key"},
                {"name": "hashed", "hash": hash_key("hashed-key"), "expires": "2030-01-01T00:00:00Z"},
            ],
        },
    )
    return tmp_path


def client_for(path: Path) -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    log_in_as_system_admin(app)
    app.include_router(TokensRouter(FileTokensPersistence(path)).router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    return client_for(tmp_data)


def test_all_lists_the_tokens_without_their_keys_or_hashes(client: TestClient):
    r = client.get(TOKENS)

    assert r.status_code == 200
    assert r.json() == [
        {"name": "plain", "description": "By hand", "expires": None},
        {"name": "hashed", "description": None, "expires": "2030-01-01T00:00:00Z"},
    ]
    assert "plain-key" not in r.text and "sha256" not in r.text


def test_all_is_empty_without_auth(tmp_path: Path):
    write_community(tmp_path, None)

    assert client_for(tmp_path).get(TOKENS).json() == []


def test_get_returns_one_token_without_its_key(client: TestClient):
    r = client.get(f"{TOKENS}/plain")

    assert r.status_code == 200
    assert r.json() == {"name": "plain", "description": "By hand", "expires": None}


def test_get_unknown_token_returns_404(client: TestClient):
    assert client.get(f"{TOKENS}/missing").status_code == 404


def test_create_reports_a_generated_key_once_and_stores_its_hash(client: TestClient, tmp_data: Path):
    r = client.post(TOKENS, json={"name": "app", "description": "Our app"})

    assert r.status_code == 201
    key = r.json()["key"]
    assert key.startswith("cofy_")
    assert stored_token(tmp_data, "app") == {"name": "app", "description": "Our app", "hash": hash_key(key)}
    assert key not in (tmp_data / "test.yaml").read_text()
    assert key not in client.get(TOKENS).text


def test_create_ignores_a_key_in_the_body(client: TestClient, tmp_data: Path):
    """Keys are only ever generated, so a chosen one can't weaken the API."""
    r = client.post(TOKENS, json={"name": "app", "key": "chosen"})

    assert r.json()["key"] != "chosen"
    assert stored_token(tmp_data, "app")["hash"] == hash_key(r.json()["key"])


def test_a_created_key_authenticates_with_the_community_api(client: TestClient, tmp_data: Path):
    key = client.post(TOKENS, json={"name": "app"}).json()["key"]
    api = TestClient(CofyAPI.create(stored(tmp_data)))

    assert api.get("/docs", headers={"Authorization": f"Bearer {key}"}).status_code == 200
    assert api.get("/docs", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_create_adds_auth_to_a_community_without(tmp_path: Path):
    write_community(tmp_path, None)

    r = client_for(tmp_path).post(TOKENS, json={"name": "app"})

    assert r.status_code == 201
    assert stored(tmp_path)["auth"] == {"type": "token", "tokens": [{"name": "app", "hash": hash_key(r.json()["key"])}]}


def test_create_with_a_taken_name_returns_409(client: TestClient):
    assert client.post(TOKENS, json={"name": "plain"}).status_code == 409


def test_create_with_an_invalid_name_returns_422(client: TestClient):
    assert client.post(TOKENS, json={"name": "Our app"}).status_code == 422


def test_put_changes_description_and_expiry_and_keeps_the_hash(client: TestClient, tmp_data: Path):
    r = client.put(f"{TOKENS}/hashed", json={"name": "hashed", "description": "Renewed", "expires": None})

    assert r.status_code == 200
    assert r.json() == {"name": "hashed", "description": "Renewed", "expires": None}
    assert stored_token(tmp_data, "hashed") == {
        "name": "hashed",
        "description": "Renewed",
        "hash": hash_key("hashed-key"),
    }


def test_put_stores_a_plain_key_as_its_hash(client: TestClient, tmp_data: Path):
    client.put(f"{TOKENS}/plain", json={"name": "plain"})

    assert stored_token(tmp_data, "plain") == {"name": "plain", "hash": hash_key("plain-key")}


def test_put_with_a_mismatched_name_returns_422(client: TestClient):
    assert client.put(f"{TOKENS}/plain", json={"name": "other"}).status_code == 422


def test_put_unknown_token_returns_404(client: TestClient):
    assert client.put(f"{TOKENS}/missing", json={"name": "missing"}).status_code == 404


def test_delete_removes_the_token(client: TestClient, tmp_data: Path):
    assert client.delete(f"{TOKENS}/plain").status_code == 204

    assert [token["name"] for token in stored(tmp_data)["auth"]["tokens"]] == ["hashed"]


def test_delete_unknown_token_returns_404(client: TestClient):
    assert client.delete(f"{TOKENS}/missing").status_code == 404


def test_writes_raise_the_revision(client: TestClient, tmp_data: Path):
    client.post(TOKENS, json={"name": "app"})

    assert stored(tmp_data)["revision"] == 1
