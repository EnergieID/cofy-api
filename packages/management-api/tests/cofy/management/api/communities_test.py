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
from cofy.management.auth.access import Grant, Role
from cofy.management.auth.user import User
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.communities import FileCommunitiesPersistence
from cofy.management.persitance.file.grants import FileGrantsPersistence

from ..access_fixture import log_in, log_in_as_system_admin, user

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
                "secrets": [{"name": "entsoe_key", "value": API_KEY}],
                "modules": [
                    {"type": "billing", "name": "default"},
                    {
                        "type": "tariff",
                        "name": "spot",
                        "source": {"type": "entsoe_day_ahead", "api_key": {"type": "secret", "name": "entsoe_key"}},
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
    log_in_as_system_admin(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(tmp_data), grants_in(tmp_data)).router)
    return TestClient(app, raise_server_exceptions=False)


def grants_in(data: Path) -> FileGrantsPersistence:
    return FileGrantsPersistence(data / "access" / "users.yaml")


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
    log_in_as_system_admin(app)
    app.include_router(
        CommunitiesRouter(FileCommunitiesPersistence(tmp_path / "missing"), grants_in(tmp_path / "missing")).router
    )

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


def test_update_leaves_secrets_intact(client: TestClient, tmp_data: Path):
    """The write re-serializes the whole config, so the real value must reach disk again."""
    client.put("/management/communities/test", json={"title": "Renamed"})

    assert _stored(tmp_data)["secrets"] == [{"name": "entsoe_key", "value": API_KEY}]


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
    log_in_as_system_admin(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(data_dir), grants_in(data_dir)).router)

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
        "",  # empty file - safe_load returns None, not a mapping either
        "# just a comment\n",  # also parses to None
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


def test_an_empty_config_file_is_reported_as_broken_rather_than_a_blank_community(client: TestClient, tmp_data: Path):
    """A truncated file (e.g. from a crash mid-write) parses to `None`, not `{}` - it must
    surface as the corruption it is rather than silently validating as a fresh, blank
    community with every field at its default."""
    (tmp_data / "empty.yaml").write_text("")

    r = client.get("/management/communities/empty")

    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"


# ── access ────────────────────────────────────────────────────────────────


def client_as(tmp_data: Path, logged_in: User) -> TestClient:
    app = FastAPI()
    add_exception_handlers(app)
    log_in(app, logged_in)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(tmp_data), grants_in(tmp_data)).router)
    return TestClient(app, raise_server_exceptions=False)


def community_admin_client(tmp_data: Path) -> TestClient:
    return client_as(tmp_data, user("ann", grants={"test": Role.community_admin}))


def test_someone_without_any_role_is_refused_the_listing(tmp_data: Path):
    r = client_as(tmp_data, user("nobody")).get("/management/communities")

    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


def test_a_community_admin_only_sees_their_own_communities(tmp_data: Path):
    listed = community_admin_client(tmp_data).get("/management/communities").json()

    assert [c["slug"] for c in listed] == ["test"]


def test_a_community_admin_cannot_open_another_community(tmp_data: Path):
    assert community_admin_client(tmp_data).get("/management/communities/other").status_code == 403


def test_a_community_admin_can_edit_but_not_delete_their_community(tmp_data: Path):
    client = community_admin_client(tmp_data)

    assert client.put("/management/communities/test", json={"title": "Renamed"}).status_code == 200
    assert client.delete("/management/communities/test").status_code == 403


def test_a_community_admin_cannot_create_a_community(tmp_data: Path):
    r = community_admin_client(tmp_data).post("/management/communities", json={"slug": "new", "title": "New"})

    assert r.status_code == 403
    assert r.json()["code"] == "forbidden"


def test_deleting_a_community_revokes_every_role_in_it(client: TestClient, tmp_data: Path):
    grants = grants_in(tmp_data)
    for slug, email in (("test", "ann@example.com"), ("other", "ann@example.com"), ("test", "bob@example.com")):
        grants.create(slug, Grant(email=email, role=Role.community_admin))

    assert client.delete("/management/communities/test").status_code == 204

    assert grants.all("test") == []
    assert [str(grant.email) for grant in grants.all("other")] == ["ann@example.com"]


def test_a_failed_delete_leaves_the_community_without_access_rather_than_access_without_it(
    tmp_data: Path, monkeypatch: pytest.MonkeyPatch
):
    grants = grants_in(tmp_data)
    grants.create("test", Grant(email="ann@example.com", role=Role.community_admin))

    def failing_delete(self, slug: str) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(FileCommunitiesPersistence, "delete", failing_delete)
    app = FastAPI()
    add_exception_handlers(app)
    log_in_as_system_admin(app)
    app.include_router(CommunitiesRouter(FileCommunitiesPersistence(tmp_data), grants).router)

    assert TestClient(app, raise_server_exceptions=False).delete("/management/communities/test").status_code == 500

    assert (tmp_data / "test.yaml").exists()
    assert grants.all("test") == []


def test_deleting_a_community_that_does_not_exist_leaves_grants_alone(client: TestClient, tmp_data: Path):
    grants = grants_in(tmp_data)
    grants.create("missing", Grant(email="ann@example.com", role=Role.community_admin))

    assert client.delete("/management/communities/missing").status_code == 404

    assert [str(grant.email) for grant in grants.all("missing")] == ["ann@example.com"]
