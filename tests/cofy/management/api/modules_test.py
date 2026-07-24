"""Integration tests for ModulesRouter with FileModulesPersistence.

Each test creates a fresh temporary directory with a minimal community YAML file,
wires up the full router, and exercises the HTTP API via TestClient.
File-level assertions are used where a mutation should have persisted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.modules import ModulesRouter
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.modules import FileModulesPersistence

# ── fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_data(tmp_path: Path):
    """Return a temp directory pre-populated with a single community 'test'."""
    community = {
        "type": "cofy_api",
        "modules": [
            {
                "type": "billing",
                "name": "default",
            },
            {
                "type": "tariff",
                "name": "spot",
                "source": {
                    "type": "entsoe_day_ahead",
                    "api_key": "secret-key",
                    "country_code": "BE",
                },
            },
        ],
    }
    (tmp_path / "test.yaml").write_text(yaml.safe_dump(community))
    return tmp_path


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    """Return a TestClient wired to the full router + file persistence in tmp_data."""
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(ModulesRouter(FileModulesPersistence(tmp_data)).router)
    return TestClient(app, raise_server_exceptions=False)


# ── helper ────────────────────────────────────────────────────────────────


def _read_modules(tmp_data: Path) -> list[dict]:
    data = yaml.safe_load((tmp_data / "test.yaml").read_text())
    return data.get("modules", [])


# ── GET /all ──────────────────────────────────────────────────────────────


def test_all_returns_existing_modules(client: TestClient):
    r = client.get("/management/communities/test/modules")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    types = {m["type"] for m in data}
    assert types == {"billing", "tariff"}


def test_all_includes_subtype_fields(client: TestClient):
    """Source-specific fields (api_key, country_code) must appear in the response."""
    r = client.get("/management/communities/test/modules")
    assert r.status_code == 200
    tariff = next(m for m in r.json() if m["type"] == "tariff")
    assert tariff["source"]["api_key"] == "secret-key"
    assert tariff["source"]["country_code"] == "BE"


def test_all_unknown_community_returns_404(client: TestClient):
    r = client.get("/management/communities/unknown/modules")
    assert r.status_code == 404


# ── GET /{module_type}/{name} ─────────────────────────────────────────────


def test_get_existing_module(client: TestClient):
    r = client.get("/management/communities/test/modules/billing/default")
    assert r.status_code == 200
    assert r.json()["type"] == "billing"
    assert r.json()["name"] == "default"


def test_get_preserves_source_fields(client: TestClient):
    r = client.get("/management/communities/test/modules/tariff/spot")
    assert r.status_code == 200
    source = r.json()["source"]
    assert source["type"] == "entsoe_day_ahead"
    assert source["api_key"] == "secret-key"


def test_get_unknown_module_returns_404(client: TestClient):
    r = client.get("/management/communities/test/modules/tariff/missing")
    assert r.status_code == 404


# ── POST / (create) ───────────────────────────────────────────────────────


def test_create_new_module(client: TestClient, tmp_data: Path):
    payload = {"type": "billing", "name": "extra"}
    r = client.post("/management/communities/test/modules", json=payload)
    assert r.status_code == 201
    assert r.json()["name"] == "extra"

    # Verify the file was updated
    saved = _read_modules(tmp_data)
    assert any(m["type"] == "billing" and m["name"] == "extra" for m in saved)


def test_create_duplicate_module_returns_409(client: TestClient):
    payload = {"type": "billing", "name": "default"}
    r = client.post("/management/communities/test/modules", json=payload)
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_resource_already_exists_handler_returns_409(tmp_data: Path):
    """ResourceAlreadyExistsError raised by persistence is mapped to 409."""
    from unittest.mock import MagicMock

    mock_persistence = MagicMock()
    from cofy.management.errors import ResourceAlreadyExistsError

    mock_persistence.create.side_effect = ResourceAlreadyExistsError("already exists")

    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(ModulesRouter(mock_persistence).router)
    c = TestClient(app, raise_server_exceptions=False)

    r = c.post("/management/communities/test/modules", json={"type": "billing", "name": "default"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_community_with_invalid_yaml_returns_error(tmp_data: Path):
    """A community YAML that is not a mapping raises a 500 error (ValueError from base)."""
    (tmp_data / "bad.yaml").write_text("- just\n- a\n- list\n")

    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(ModulesRouter(FileModulesPersistence(tmp_data)).router)
    bad_client = TestClient(app, raise_server_exceptions=False)

    r = bad_client.get("/management/communities/bad/modules")
    assert r.status_code == 422


def test_create_persists_source_settings(client: TestClient, tmp_data: Path):
    payload = {
        "type": "tariff",
        "name": "new_spot",
        "source": {"type": "entsoe_day_ahead", "api_key": "new-key", "country_code": "NL"},
    }
    r = client.post("/management/communities/test/modules", json=payload)
    assert r.status_code == 201

    saved = _read_modules(tmp_data)
    new_module = next((m for m in saved if m["name"] == "new_spot"), None)
    assert new_module is not None
    assert new_module["source"]["api_key"] == "new-key"
    assert new_module["source"]["country_code"] == "NL"


# ── PUT /{module_type}/{name} (replace) ───────────────────────────────────


def test_put_replaces_module(client: TestClient, tmp_data: Path):
    payload = {
        "type": "tariff",
        "name": "spot",
        "source": {"type": "entsoe_day_ahead", "api_key": "replaced-key", "country_code": "DE"},
    }
    r = client.put("/management/communities/test/modules/tariff/spot", json=payload)
    assert r.status_code == 200
    assert r.json()["source"]["api_key"] == "replaced-key"

    # Verify file reflects the change
    saved = _read_modules(tmp_data)
    spot = next(m for m in saved if m["name"] == "spot")
    assert spot["source"]["api_key"] == "replaced-key"
    assert spot["source"]["country_code"] == "DE"


def test_put_unknown_module_returns_404(client: TestClient):
    payload = {"type": "billing", "name": "ghost"}
    r = client.put("/management/communities/test/modules/billing/ghost", json=payload)
    assert r.status_code == 404


# ── PATCH /{module_type}/{name} (partial update) ──────────────────────────


def test_patch_updates_description(client: TestClient, tmp_data: Path):
    patch = {"type": "billing", "name": "default", "description": "Updated desc"}
    r = client.patch("/management/communities/test/modules/billing/default", json=patch)
    assert r.status_code == 200
    assert r.json()["description"] == "Updated desc"

    saved = _read_modules(tmp_data)
    billing = next(m for m in saved if m["name"] == "default")
    assert billing.get("description") == "Updated desc"


def test_patch_unknown_module_returns_404(client: TestClient):
    patch = {"type": "billing", "name": "ghost", "description": "x"}
    r = client.patch("/management/communities/test/modules/billing/ghost", json=patch)
    assert r.status_code == 404


# ── DELETE /{module_type}/{name} ──────────────────────────────────────────


def test_delete_removes_module(client: TestClient, tmp_data: Path):
    r = client.delete("/management/communities/test/modules/billing/default")
    assert r.status_code == 204

    saved = _read_modules(tmp_data)
    assert not any(m["type"] == "billing" and m["name"] == "default" for m in saved)


def test_delete_unknown_module_returns_404(client: TestClient):
    r = client.delete("/management/communities/test/modules/billing/ghost")
    assert r.status_code == 404


def test_delete_does_not_affect_other_modules(client: TestClient, tmp_data: Path):
    client.delete("/management/communities/test/modules/billing/default")

    saved = _read_modules(tmp_data)
    assert any(m["type"] == "tariff" and m["name"] == "spot" for m in saved)
