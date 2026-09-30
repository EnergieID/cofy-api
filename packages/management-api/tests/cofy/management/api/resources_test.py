"""Integration tests for ResourcesRouter and AllowedResourcesRouter with file persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cofy.api import MASK
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.allowed_resources import AllowedResourcesRouter
from cofy.management.api.modules import ModulesRouter
from cofy.management.api.resources import ResourcesRouter
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.modules import FileModulesPersistence
from cofy.management.persitance.file.resources import FileResourcesPersistence

RESOURCES = "/management/communities/test/resources"
MODULES = "/management/communities/test/modules"


def ref(name: str) -> dict:
    return {"type": "ref", "name": name}


# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_data(tmp_path: Path):
    """A community with a secret, a source resource using it, and a module using the source."""
    community = {
        "type": "cofy_api",
        "resources": [
            {"type": "secret", "name": "entsoe_key", "value": "secret-key"},
            {
                "type": "source",
                "name": "day_ahead",
                "value": {"type": "entsoe_day_ahead", "api_key": ref("entsoe_key"), "country_code": "BE"},
            },
            {"type": "secret", "name": "unused", "value": "other-key"},
        ],
        "modules": [{"type": "tariff", "name": "spot", "source": ref("day_ahead")}],
    }
    (tmp_path / "test.yaml").write_text(yaml.safe_dump(community))
    return tmp_path


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    modules = FileModulesPersistence(tmp_data)
    app.include_router(ResourcesRouter(FileResourcesPersistence(tmp_data), modules).router)
    app.include_router(ModulesRouter(modules).router)
    app.include_router(AllowedResourcesRouter().router)
    return TestClient(app, raise_server_exceptions=False)


def _stored(tmp_data: Path) -> dict:
    return yaml.safe_load((tmp_data / "test.yaml").read_text())


def _stored_resource(tmp_data: Path, name: str) -> dict:
    return next(resource for resource in _stored(tmp_data)["resources"] if resource["name"] == name)


# ── reads ─────────────────────────────────────────────────────────────────


def test_all_lists_the_resources_with_secrets_masked(client: TestClient):
    r = client.get(RESOURCES)

    assert r.status_code == 200
    assert [resource["name"] for resource in r.json()] == ["entsoe_key", "day_ahead", "unused"]
    assert r.json()[0]["value"] == MASK
    assert "secret-key" not in r.text


def test_get_returns_one_resource_with_its_references(client: TestClient):
    r = client.get(f"{RESOURCES}/day_ahead")

    assert r.status_code == 200
    assert r.json()["value"]["api_key"] == ref("entsoe_key")


def test_get_unknown_resource_returns_404(client: TestClient):
    assert client.get(f"{RESOURCES}/missing").status_code == 404


def test_usages_lists_the_modules_and_resources_referencing_a_resource(client: TestClient):
    assert client.get(f"{RESOURCES}/day_ahead/usages").json() == {
        "modules": [{"type": "tariff", "name": "spot"}],
        "resources": [],
    }
    assert client.get(f"{RESOURCES}/entsoe_key/usages").json() == {"modules": [], "resources": ["day_ahead"]}
    assert client.get(f"{RESOURCES}/unused/usages").json() == {"modules": [], "resources": []}


# ── writes ────────────────────────────────────────────────────────────────


def test_create_stores_the_resource(client: TestClient, tmp_data: Path):
    r = client.post(RESOURCES, json={"type": "secret", "name": "new_key", "value": "new"})

    assert r.status_code == 201
    assert _stored_resource(tmp_data, "new_key")["value"] == "new"


def test_create_with_a_taken_name_returns_409(client: TestClient):
    r = client.post(RESOURCES, json={"type": "secret", "name": "unused", "value": "x"})

    assert r.status_code == 409


def test_put_keeps_a_masked_secret(client: TestClient, tmp_data: Path):
    r = client.put(
        f"{RESOURCES}/entsoe_key",
        json={"type": "secret", "name": "entsoe_key", "value": MASK, "description": "ENTSO-E"},
    )

    assert r.status_code == 200
    stored = _stored_resource(tmp_data, "entsoe_key")
    assert stored["value"] == "secret-key"
    assert stored["description"] == "ENTSO-E"


def test_put_cannot_rename_a_resource(client: TestClient):
    r = client.put(f"{RESOURCES}/unused", json={"type": "secret", "name": "renamed", "value": "x"})

    assert r.status_code == 422


def test_put_that_breaks_a_reference_is_rejected_and_stores_nothing(client: TestClient, tmp_data: Path):
    """The tariff module references `day_ahead` as a price source, so it can't become a secret."""
    before = (tmp_data / "test.yaml").read_text()

    r = client.put(f"{RESOURCES}/day_ahead", json={"type": "secret", "name": "day_ahead", "value": "x"})

    assert r.status_code == 422
    assert "is a secret, where a source is expected" in r.json()["detail"]
    assert (tmp_data / "test.yaml").read_text() == before


def test_delete_an_unused_resource(client: TestClient, tmp_data: Path):
    assert client.delete(f"{RESOURCES}/unused").status_code == 204
    assert "unused" not in [resource["name"] for resource in _stored(tmp_data)["resources"]]


def test_delete_a_resource_in_use_returns_409_naming_its_users(client: TestClient, tmp_data: Path):
    r = client.delete(f"{RESOURCES}/day_ahead")

    assert r.status_code == 409
    assert r.json()["code"] == "resource-in-use"
    assert "module tariff:spot" in r.json()["detail"]
    assert "day_ahead" in [resource["name"] for resource in _stored(tmp_data)["resources"]]


def test_a_module_referencing_an_unknown_resource_is_rejected_and_stores_nothing(client: TestClient, tmp_data: Path):
    before = (tmp_data / "test.yaml").read_text()

    r = client.put(f"{MODULES}/tariff/spot", json={"type": "tariff", "name": "spot", "source": ref("missing")})

    assert r.status_code == 422
    assert "unknown resource 'missing'" in r.json()["detail"]
    assert (tmp_data / "test.yaml").read_text() == before


# ── allowed resources ─────────────────────────────────────────────────────


def test_allowed_resources_lists_every_kind_with_its_schema(client: TestClient):
    r = client.get("/management/communities/test/allowed-resources")

    assert r.status_code == 200
    kinds = {entry["type"]: entry for entry in r.json()}
    assert {"secret", "tariff", "source"} == set(kinds)
    assert "resource" not in kinds
    assert kinds["secret"]["description"] == "A credential."
    assert kinds["source"]["description"] == "A timeseries source, built once and shared by every reference to it."
    value, _ref = kinds["source"]["schema"]["properties"]["value"]["oneOf"]
    assert "entsoe_day_ahead" in value["discriminator"]["mapping"]
