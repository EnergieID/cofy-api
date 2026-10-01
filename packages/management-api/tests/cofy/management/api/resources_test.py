"""Integration tests for ResourcesRouter and AllowedResourcesRouter with file persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .community_fixture import COMMUNITY, client_for, ref, stored, write_community

RESOURCES = f"{COMMUNITY}/resources"
MODULES = f"{COMMUNITY}/modules"


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    write_community(tmp_path)
    return tmp_path


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    return client_for(tmp_data)


def _stored_resource(tmp_data: Path, name: str) -> dict:
    return next(resource for resource in stored(tmp_data)["resources"] if resource["name"] == name)


def entsoe(api_key: str = "entsoe_key") -> dict:
    return {"type": "entsoe_day_ahead", "api_key": {"type": "secret", "name": api_key}}


# ── reads ─────────────────────────────────────────────────────────────────


def test_all_lists_the_resources_with_secrets_by_name(client: TestClient):
    r = client.get(RESOURCES)

    assert r.status_code == 200
    assert [resource["name"] for resource in r.json()] == ["day_ahead", "unused"]
    assert r.json()[0]["value"]["api_key"] == {"type": "secret", "name": "entsoe_key"}
    assert "secret-key" not in r.text


def test_get_unknown_resource_returns_404(client: TestClient):
    assert client.get(f"{RESOURCES}/missing").status_code == 404


# ── writes ────────────────────────────────────────────────────────────────


def test_create_stores_the_resource(client: TestClient, tmp_data: Path):
    r = client.post(RESOURCES, json={"type": "source", "name": "nl", "value": entsoe() | {"country_code": "NL"}})

    assert r.status_code == 201
    assert _stored_resource(tmp_data, "nl")["value"]["country_code"] == "NL"


def test_create_with_a_taken_name_returns_409(client: TestClient):
    assert client.post(RESOURCES, json={"type": "source", "name": "unused", "value": entsoe()}).status_code == 409


def test_create_naming_an_unknown_secret_is_rejected(client: TestClient):
    r = client.post(RESOURCES, json={"type": "source", "name": "nl", "value": entsoe("missing")})

    assert r.status_code == 422
    assert "unknown secret 'missing'" in r.json()["detail"]


def test_put_replaces_the_resource(client: TestClient, tmp_data: Path):
    r = client.put(
        f"{RESOURCES}/unused", json={"type": "source", "name": "unused", "value": entsoe(), "description": "x"}
    )

    assert r.status_code == 200
    assert _stored_resource(tmp_data, "unused")["description"] == "x"


def test_put_cannot_rename_a_resource(client: TestClient):
    assert (
        client.put(f"{RESOURCES}/unused", json={"type": "source", "name": "renamed", "value": entsoe()}).status_code
        == 422
    )


def test_put_that_breaks_a_reference_is_rejected_and_stores_nothing(client: TestClient, tmp_data: Path):
    """The tariff module references `day_ahead` as a price source, so it can't become a tariff."""
    before = (tmp_data / "test.yaml").read_text()
    tariff = [{"start": "2024-01-01T00:00:00+01:00", "consumption": {"constant_cost": 1.0}}]

    r = client.put(f"{RESOURCES}/day_ahead", json={"type": "tariff", "name": "day_ahead", "value": tariff})

    assert r.status_code == 422
    assert "is a tariff, where a source is expected" in r.json()["detail"]
    assert (tmp_data / "test.yaml").read_text() == before


def test_a_put_refused_by_the_whole_configuration_quotes_none_of_its_secrets(client: TestClient, tmp_data: Path):
    """Fine on its own, but the tariff module referencing `day_ahead` takes prices, not production."""
    production = {"type": "energyid_production", "api_key": {"type": "secret", "name": "entsoe_key"}, "record_id": "r"}

    r = client.put(f"{RESOURCES}/day_ahead", json={"type": "source", "name": "day_ahead", "value": production})

    assert r.status_code == 422
    assert "holds a energyid_production source" in r.json()["detail"]
    for value in ("secret-key", "spare-secret"):
        assert value not in r.text


def test_delete_an_unused_resource(client: TestClient, tmp_data: Path):
    assert client.delete(f"{RESOURCES}/unused").status_code == 204
    assert "unused" not in [resource["name"] for resource in stored(tmp_data)["resources"]]


def test_delete_a_resource_in_use_returns_409_naming_its_users(client: TestClient, tmp_data: Path):
    r = client.delete(f"{RESOURCES}/day_ahead")

    assert r.status_code == 409
    assert r.json()["code"] == "resource-in-use"
    assert "module tariff:spot" in r.json()["detail"]
    assert "day_ahead" in [resource["name"] for resource in stored(tmp_data)["resources"]]


def test_a_module_referencing_an_unknown_resource_is_rejected_and_stores_nothing(client: TestClient, tmp_data: Path):
    before = (tmp_data / "test.yaml").read_text()

    r = client.put(f"{MODULES}/tariff/spot", json={"type": "tariff", "name": "spot", "source": ref("missing")})

    assert r.status_code == 422
    assert "unknown resource 'missing'" in r.json()["detail"]
    assert (tmp_data / "test.yaml").read_text() == before


# ── allowed resources ─────────────────────────────────────────────────────


def test_allowed_resources_lists_every_kind_with_its_schema(client: TestClient):
    r = client.get(f"{COMMUNITY}/allowed-resources")

    assert r.status_code == 200
    kinds = {entry["type"]: entry for entry in r.json()}
    assert {"tariff", "source"} == set(kinds)
    assert kinds["source"]["description"] == "A timeseries source, built once and shared by every reference to it."
    value, _ref = kinds["source"]["schema"]["properties"]["value"]["oneOf"]
    assert "entsoe_day_ahead" in value["discriminator"]["mapping"]
