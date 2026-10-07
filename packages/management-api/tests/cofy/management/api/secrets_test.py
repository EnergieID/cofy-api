"""Integration tests for SecretsRouter: secrets are written, never read back."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .community_fixture import COMMUNITY, client_for, stored, write_community

SECRETS = f"{COMMUNITY}/secrets"


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    write_community(tmp_path)
    return tmp_path


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    return client_for(tmp_data)


def _stored_secret(tmp_data: Path, name: str) -> dict:
    return next(secret for secret in stored(tmp_data)["secrets"] if secret["name"] == name)


def test_all_lists_the_secrets_without_their_values(client: TestClient):
    r = client.get(SECRETS)

    assert r.status_code == 200
    assert r.json() == [
        {"name": "entsoe_key", "description": "ENTSO-E"},
        {"name": "spare_key", "description": None},
    ]
    assert "secret-key" not in r.text and "spare-secret" not in r.text


def test_get_returns_one_secret_without_its_value(client: TestClient):
    r = client.get(f"{SECRETS}/entsoe_key")

    assert r.status_code == 200
    assert "secret-key" not in r.text


def test_get_unknown_secret_returns_404(client: TestClient):
    assert client.get(f"{SECRETS}/missing").status_code == 404


def test_create_stores_the_value_and_reports_it_without(client: TestClient, tmp_data: Path):
    r = client.post(SECRETS, json={"name": "new_key", "value": "new-secret"})

    assert r.status_code == 201
    assert "new-secret" not in r.text
    assert _stored_secret(tmp_data, "new_key")["value"] == "new-secret"


def test_create_cannot_read_a_secret_from_the_environment(client: TestClient, tmp_data: Path):
    """The environment holds the deployment's own secrets, which no community may reach."""
    before = (tmp_data / "test.yaml").read_text()

    r = client.post(SECRETS, json={"name": "from_env", "value": {"env": "ENTSOE_API_KEY"}})

    assert r.status_code == 422
    assert (tmp_data / "test.yaml").read_text() == before


def test_create_with_a_taken_name_returns_409(client: TestClient):
    assert client.post(SECRETS, json={"name": "entsoe_key", "value": "x"}).status_code == 409


def test_put_overwrites_the_value(client: TestClient, tmp_data: Path):
    r = client.put(f"{SECRETS}/entsoe_key", json={"name": "entsoe_key", "value": "rotated", "description": "new"})

    assert r.status_code == 200
    assert _stored_secret(tmp_data, "entsoe_key") == {"name": "entsoe_key", "description": "new", "value": "rotated"}


def test_put_needs_the_value(client: TestClient):
    """There's nothing to keep: a write always says what the secret is."""
    assert client.put(f"{SECRETS}/entsoe_key", json={"name": "entsoe_key", "description": "new"}).status_code == 422


def test_put_cannot_rename_a_secret(client: TestClient):
    assert client.put(f"{SECRETS}/entsoe_key", json={"name": "renamed", "value": "x"}).status_code == 422


def test_delete_an_unused_secret(client: TestClient, tmp_data: Path):
    assert client.delete(f"{SECRETS}/spare_key").status_code == 204
    assert [secret["name"] for secret in stored(tmp_data)["secrets"]] == ["entsoe_key"]


def test_delete_a_secret_in_use_returns_409_naming_its_users(client: TestClient, tmp_data: Path):
    r = client.delete(f"{SECRETS}/entsoe_key")

    assert r.status_code == 409
    assert "resource day_ahead" in r.json()["detail"]
    assert "entsoe_key" in [secret["name"] for secret in stored(tmp_data)["secrets"]]


def test_delete_unknown_secret_returns_404(client: TestClient):
    assert client.delete(f"{SECRETS}/missing").status_code == 404
