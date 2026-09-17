"""Integration tests for CommunitiesRouter with FileCommunitiesPersistence.

The load-bearing property here is containment: a community's own settings are editable
without the request carrying - or the write disturbing - the modules and credentials stored
alongside them.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.communities import CommunitiesRouter
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.communities import FileCommunitiesPersistence

TOKEN = "super-secret-token"
API_KEY = "secret-key"


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    """Two communities; 'test' has modules, an auth block and a credential."""
    (tmp_path / "test.yaml").write_text(
        yaml.safe_dump(
            {
                "type": "cofy_api",
                "title": "Test community",
                "description": "For tests",
                "modules": [
                    {"type": "billing", "name": "default"},
                    {
                        "type": "tariff",
                        "name": "spot",
                        "source": {"type": "entsoe_day_ahead", "api_key": API_KEY},
                    },
                ],
                "auth": {"type": "token", "tokens": {TOKEN: {"name": "M2M"}}},
            }
        )
    )
    (tmp_path / "other.yaml").write_text(yaml.safe_dump({"type": "cofy_api", "title": "Other", "modules": []}))
    return tmp_path


@pytest.fixture()
def client(tmp_data: Path) -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(tmp_data)).router)
    return TestClient(app, raise_server_exceptions=False)


def _stored(tmp_data: Path, slug: str = "test") -> dict:
    return yaml.safe_load((tmp_data / f"{slug}.yaml").read_text())


# ── GET / ─────────────────────────────────────────────────────────────────


def test_lists_every_community(client: TestClient):
    r = client.get("/management/communities")

    assert r.status_code == 200
    assert [c["slug"] for c in r.json()] == ["other", "test"]  # sorted, for a stable UI order


def test_listing_reports_module_counts(client: TestClient):
    listed = {c["slug"]: c["module_count"] for c in client.get("/management/communities").json()}

    assert listed == {"test": 2, "other": 0}


def test_listing_is_empty_when_no_communities_exist(tmp_path: Path):
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(tmp_path / "missing")).router)

    r = TestClient(app).get("/management/communities")

    assert r.status_code == 200
    assert r.json() == []


# ── containment: what a community response does and does not include ──────


def test_response_omits_the_modules(client: TestClient):
    """Modules are managed through their own endpoints."""
    body = client.get("/management/communities/test").json()

    assert "modules" not in body
    assert body["module_count"] == 2  # a count is useful; the contents are not this endpoint's


def test_response_never_includes_the_auth_block(client: TestClient):
    """`TokenAuthSettings.tokens` is keyed *by the token*, so exposing auth would publish
    every machine-to-machine credential - and a mapping key cannot be masked."""
    r = client.get("/management/communities/test")

    assert "auth" not in r.json()
    assert TOKEN not in r.text


def test_response_never_includes_module_credentials(client: TestClient):
    assert API_KEY not in client.get("/management/communities/test").text
    assert API_KEY not in client.get("/management/communities").text


def test_get_unknown_community_returns_404(client: TestClient):
    assert client.get("/management/communities/nope").status_code == 404


# ── PUT /{slug} ───────────────────────────────────────────────────────────


def test_update_changes_the_community_fields(client: TestClient, tmp_data: Path):
    r = client.put(
        "/management/communities/test",
        json={"title": "Renamed", "description": "Updated", "debug_mode": True},
    )

    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"
    stored = _stored(tmp_data)
    assert stored["title"] == "Renamed"
    assert stored["description"] == "Updated"
    assert stored["debug_mode"] is True


def test_update_leaves_modules_untouched(client: TestClient, tmp_data: Path):
    """The whole point of excluding modules from the request body."""
    client.put("/management/communities/test", json={"title": "Renamed"})

    stored = _stored(tmp_data)
    assert [(m["type"], m["name"]) for m in stored["modules"]] == [("billing", "default"), ("tariff", "spot")]


def test_update_leaves_module_credentials_intact(client: TestClient, tmp_data: Path):
    """The write re-serializes the whole config, so a masked secret must not reach disk."""
    client.put("/management/communities/test", json={"title": "Renamed"})

    spot = next(m for m in _stored(tmp_data)["modules"] if m["name"] == "spot")
    assert spot["source"]["api_key"] == API_KEY


def test_update_leaves_the_auth_block_intact(client: TestClient, tmp_data: Path):
    client.put("/management/communities/test", json={"title": "Renamed"})

    assert _stored(tmp_data)["auth"]["tokens"] == {TOKEN: {"name": "M2M"}}


def test_update_unknown_community_returns_404(client: TestClient):
    assert client.put("/management/communities/nope", json={"title": "x"}).status_code == 404


# ── POST / ────────────────────────────────────────────────────────────────


def test_create_writes_a_new_community(client: TestClient, tmp_data: Path):
    r = client.post("/management/communities", json={"slug": "fresh", "title": "Fresh"})

    assert r.status_code == 201
    assert r.json() == {
        "slug": "fresh",
        "title": "Fresh",
        "description": "",
        "debug_mode": False,
        "module_count": 0,
    }
    assert _stored(tmp_data, "fresh")["title"] == "Fresh"


def test_created_community_appears_in_the_listing(client: TestClient):
    client.post("/management/communities", json={"slug": "fresh", "title": "Fresh"})

    assert "fresh" in {c["slug"] for c in client.get("/management/communities").json()}


def test_create_duplicate_slug_returns_409(client: TestClient, tmp_data: Path):
    before = (tmp_data / "test.yaml").read_bytes()

    r = client.post("/management/communities", json={"slug": "test", "title": "Hijack"})

    assert r.status_code == 409
    assert (tmp_data / "test.yaml").read_bytes() == before  # the existing config is untouched


def test_create_in_a_missing_data_directory_creates_it(tmp_path: Path):
    data_dir = tmp_path / "not-yet"
    app = FastAPI()
    add_exception_handlers(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(data_dir)).router)

    r = TestClient(app).post("/management/communities", json={"slug": "first", "title": "First"})

    assert r.status_code == 201
    assert (data_dir / "first.yaml").exists()


@pytest.mark.parametrize("slug", ["../escape", "a/b", ".", "", "with space", "sub/../dir"])
def test_create_rejects_a_slug_that_is_not_a_safe_filename(client: TestClient, slug: str, tmp_data: Path):
    """The slug becomes a filename, and on create it arrives in the body where no path
    converter is protecting it."""
    r = client.post("/management/communities", json={"slug": slug, "title": "Bad"})

    assert r.status_code == 422
    assert sorted(tmp_data.glob("*.yaml")) == [tmp_data / "other.yaml", tmp_data / "test.yaml"]


# ── DELETE /{slug} ────────────────────────────────────────────────────────


def test_delete_removes_the_community(client: TestClient, tmp_data: Path):
    r = client.delete("/management/communities/other")

    assert r.status_code == 204
    assert not (tmp_data / "other.yaml").exists()
    assert (tmp_data / "test.yaml").exists()


def test_delete_unknown_community_returns_404(client: TestClient):
    assert client.delete("/management/communities/nope").status_code == 404


# ── resilience: one broken config must not hide the rest ──────────────────


def test_listing_skips_an_unreadable_community(client: TestClient, tmp_data: Path):
    """These files are hand-editable, and this listing is the console's entry point - one bad
    edit must not make every community unreachable."""
    (tmp_data / "broken.yaml").write_text("type: cofy-api\ntitle: wrong discriminator\n")

    r = client.get("/management/communities")

    assert r.status_code == 200
    assert [c["slug"] for c in r.json()] == ["other", "test"]


@pytest.mark.parametrize(
    "content",
    [
        "type: cofy-api\n",  # discriminator that does not validate
        "- just\n- a\n- list\n",  # not a mapping
        "title: [unclosed\n",  # not even YAML
    ],
)
def test_listing_survives_every_kind_of_broken_config(client: TestClient, tmp_data: Path, content: str):
    (tmp_data / "broken.yaml").write_text(content)

    r = client.get("/management/communities")

    assert r.status_code == 200
    assert {c["slug"] for c in r.json()} == {"other", "test"}


def test_reading_a_broken_community_directly_still_reports_the_error(client: TestClient, tmp_data: Path):
    """Skipping it from the listing must not make the problem undiagnosable."""
    (tmp_data / "broken.yaml").write_text("type: cofy-api\n")

    r = client.get("/management/communities/broken")

    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"
