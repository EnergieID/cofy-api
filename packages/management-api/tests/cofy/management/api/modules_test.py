"""Integration tests for ModulesRouter with FileModulesPersistence.

Each test creates a fresh temporary directory with a minimal community YAML file,
wires up the full router, and exercises the HTTP API via TestClient.
File-level assertions are used where a mutation should have persisted.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from cofy.api import MASK
from cofy.api.module import ModuleSettings
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
    """Source-specific fields must appear in the response, with secrets masked."""
    r = client.get("/management/communities/test/modules")
    assert r.status_code == 200
    tariff = next(m for m in r.json() if m["type"] == "tariff")
    assert tariff["source"]["api_key"] == MASK
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
    assert source["api_key"] == MASK


def test_get_never_leaks_the_stored_secret(client: TestClient, tmp_data: Path):
    """The real credential stays on disk and never reaches a response body."""
    assert "secret-key" in (tmp_data / "test.yaml").read_text()
    r = client.get("/management/communities/test/modules/tariff/spot")
    assert "secret-key" not in r.text


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
    assert r.json()["source"]["api_key"] == MASK  # response is masked, even for a new secret

    # Verify file reflects the change
    saved = _read_modules(tmp_data)
    spot = next(m for m in saved if m["name"] == "spot")
    assert spot["source"]["api_key"] == "replaced-key"
    assert spot["source"]["country_code"] == "DE"


def test_put_unknown_module_returns_404(client: TestClient):
    payload = {"type": "billing", "name": "ghost"}
    r = client.put("/management/communities/test/modules/billing/ghost", json=payload)
    assert r.status_code == 404


def test_put_rejects_body_type_mismatch(client: TestClient, tmp_data: Path):
    """A PUT body describing a different module type than the URL must be rejected, not
    silently overwrite the addressed module with an unrelated one."""
    payload = {"type": "billing", "name": "default"}
    r = client.put("/management/communities/test/modules/tariff/spot", json=payload)
    assert r.status_code == 422

    saved = _read_modules(tmp_data)
    assert any(m["type"] == "tariff" and m["name"] == "spot" for m in saved)  # untouched
    assert sum(1 for m in saved if m["type"] == "billing" and m["name"] == "default") == 1  # no duplicate


def test_put_rejects_body_name_mismatch(client: TestClient, tmp_data: Path):
    payload = {
        "type": "tariff",
        "name": "renamed",
        "source": {"type": "entsoe_day_ahead", "api_key": "k"},
    }
    r = client.put("/management/communities/test/modules/tariff/spot", json=payload)
    assert r.status_code == 422

    saved = _read_modules(tmp_data)
    assert any(m["type"] == "tariff" and m["name"] == "spot" for m in saved)  # untouched
    assert not any(m["name"] == "renamed" for m in saved)


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


# ── FileModulesPersistence.replace: defense in depth ──────────────────────


def test_replace_rejects_collision_with_a_different_existing_module(tmp_data: Path):
    """Called directly - bypassing ModulesRouter's own identity check - replace() must
    still refuse to turn the addressed module into a duplicate of an unrelated one."""
    from cofy.modules.billing import BillingModuleSettings

    from cofy.management.errors import ResourceAlreadyExistsError

    persistence = FileModulesPersistence(tmp_data)
    colliding = BillingModuleSettings(name="default")  # already exists under a different slot

    with pytest.raises(ResourceAlreadyExistsError):
        persistence.replace("test", "tariff", "spot", colliding)

    saved = _read_modules(tmp_data)
    assert any(m["type"] == "tariff" and m["name"] == "spot" for m in saved)  # untouched
    assert sum(1 for m in saved if m["type"] == "billing" and m["name"] == "default") == 1  # no duplicate


# ── masked secrets on a full-replace PUT ──────────────────────────────────


def test_put_with_masked_secret_keeps_the_stored_value(client: TestClient, tmp_data: Path):
    """The GET -> edit -> PUT round trip must not blank out an untouched credential."""
    stored = client.get("/management/communities/test/modules/tariff/spot").json()
    assert stored["source"]["api_key"] == MASK

    stored["display_name"] = "Spot prices"  # edit something unrelated, send the mask back
    r = client.put("/management/communities/test/modules/tariff/spot", json=stored)
    assert r.status_code == 200

    spot = next(m for m in _read_modules(tmp_data) if m["name"] == "spot")
    assert spot["source"]["api_key"] == "secret-key"  # original survived
    assert spot["display_name"] == "Spot prices"


def test_put_with_a_real_secret_overwrites_the_stored_value(client: TestClient, tmp_data: Path):
    """Sending an actual value - rather than the mask - still sets a new secret."""
    stored = client.get("/management/communities/test/modules/tariff/spot").json()
    stored["source"]["api_key"] = "rotated-key"

    r = client.put("/management/communities/test/modules/tariff/spot", json=stored)
    assert r.status_code == 200

    spot = next(m for m in _read_modules(tmp_data) if m["name"] == "spot")
    assert spot["source"]["api_key"] == "rotated-key"


def test_put_switching_source_type_does_not_restore_across_branches(client: TestClient, tmp_data: Path):
    """Changing the polymorphic branch leaves the incoming payload as sent."""
    payload = {
        "type": "tariff",
        "name": "spot",
        "source": {"type": "energyid_production", "api_key": "eid-key", "record_id": "r1"},
    }
    r = client.put("/management/communities/test/modules/tariff/spot", json=payload)
    assert r.status_code == 200

    spot = next(m for m in _read_modules(tmp_data) if m["name"] == "spot")
    assert spot["source"]["type"] == "energyid_production"
    assert spot["source"]["api_key"] == "eid-key"


# ── module types that may not be stored ───────────────────────────────────


def test_create_rejects_an_abstract_module_type(client: TestClient, tmp_data: Path):
    """`ModuleSettings` is registered under "module" but `Module` cannot be built, so the
    type is pruned from the union and never validates."""
    r = client.post("/management/communities/test/modules", json={"type": "module", "name": "abstract"})

    assert r.status_code == 422
    assert not any(m["type"] == "module" for m in _read_modules(tmp_data))


def test_put_rejects_an_abstract_module_type(client: TestClient, tmp_data: Path):
    r = client.put(
        "/management/communities/test/modules/module/abstract",
        json={"type": "module", "name": "abstract"},
    )

    assert r.status_code == 422
    assert len(_read_modules(tmp_data)) == 2  # nothing added or replaced


def test_create_rejects_a_type_the_community_is_not_allowed(client: TestClient, tmp_data: Path, monkeypatch):
    """Writes are checked against the same allow-list the API publishes, so a community that
    may not use a module type cannot have one stored either."""
    monkeypatch.setattr(
        "cofy.management.api.modules.allowed_module_types",
        lambda slug: {"billing": ModuleSettings.registry()["billing"]},
    )

    r = client.post(
        "/management/communities/test/modules",
        json={"type": "tariff", "name": "new", "source": {"type": "entsoe_day_ahead", "api_key": "k"}},
    )

    assert r.status_code == 422
    assert "is not allowed for community 'test'" in r.json()["detail"]
    assert not any(m["name"] == "new" for m in _read_modules(tmp_data))


def test_put_rejects_a_type_the_community_is_not_allowed(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "cofy.management.api.modules.allowed_module_types",
        lambda slug: {"billing": ModuleSettings.registry()["billing"]},
    )

    r = client.put(
        "/management/communities/test/modules/tariff/spot",
        json={"type": "tariff", "name": "spot", "source": {"type": "entsoe_day_ahead", "api_key": "k"}},
    )

    assert r.status_code == 422
    assert "is not allowed for community 'test'" in r.json()["detail"]


def test_module_body_schema_keeps_its_discriminator(client: TestClient):
    """Wrapping the union in `Body()` drops the discriminator, leaving a bare `anyOf` that
    cannot say which variant a `type` selects - and making every branch report its own
    errors."""
    app = FastAPI()
    app.include_router(ModulesRouter(FileModulesPersistence(Path("/nonexistent"))).router)

    body = app.openapi()["paths"]["/management/communities/{slug}/modules"]["post"]["requestBody"]
    schema = body["content"]["application/json"]["schema"]

    assert "oneOf" in schema
    assert schema["discriminator"]["propertyName"] == "type"
    assert "tariff" in schema["discriminator"]["mapping"]
