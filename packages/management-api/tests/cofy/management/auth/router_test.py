"""Logging in and out, with the identity provider's side of the exchange stood in for."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.auth.config import OidcConfig
from cofy.management.auth.router import AuthRouter, safe_return_to
from cofy.management.auth.session import install_session
from cofy.management.auth.user import install_users
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.communities import FileCommunitiesPersistence
from cofy.management.persitance.file.users import FileUsersPersistence

from ..access_fixture import ISSUER, OIDC_CONFIG

METADATA = {
    "issuer": ISSUER,
    "authorization_endpoint": f"{ISSUER}/connect/authorize",
    "token_endpoint": f"{ISSUER}/connect/token",
    "end_session_endpoint": f"{ISSUER}/connect/endsession",
    "userinfo_endpoint": f"{ISSUER}/connect/userinfo",
}
ANN = {
    "email": "ann@example.com",
    "name": "Ann",
    "system_admin": False,
    "permissions": [
        {
            "slug": "test",
            "permissions": [
                {"action": action, "subject": subject}
                for subject in (
                    "community",
                    "modules",
                    "resources",
                    "secrets",
                    "tokens",
                    "grants",
                    "allowed_modules",
                    "allowed_resources",
                )
                for action in ("read", "write")
                if action == "read" or not subject.startswith("allowed_")
            ],
        },
    ],
}
CLAIMS = {"iss": ISSUER, "sub": "ann-sub", "email": "ann@example.com", "email_verified": True, "name": "Ann"}


@pytest.fixture()
def data(tmp_path: Path) -> Path:
    (tmp_path / "test.yaml").write_text(yaml.safe_dump({"type": "cofy_api"}))
    # Apart from the communities, as in the data directory, or it would be listed as one.
    (tmp_path / "access").mkdir()
    users = [
        {"email": "ann@example.com", "grants": {"test": "community_admin"}},
        {"email": "root@example.com", "system_admin": True},
    ]
    (tmp_path / "access" / "users.yaml").write_text(yaml.safe_dump({"users": users}))
    return tmp_path


def stored_user(data: Path, email: str) -> dict:
    return next(u for u in yaml.safe_load((data / "access" / "users.yaml").read_text())["users"] if u["email"] == email)


def client_for(
    data: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: OidcConfig = OIDC_CONFIG,
    metadata: dict | Exception = METADATA,
    userinfo: dict | None = None,
    **claims: Any,
) -> TestClient:
    users = FileUsersPersistence(data / "access" / "users.yaml")
    router = AuthRouter(config, users, FileCommunitiesPersistence(data))

    async def load_server_metadata() -> dict:
        if isinstance(metadata, Exception):
            raise metadata
        return metadata

    async def authorize_access_token(request) -> dict:
        return {"userinfo": CLAIMS | claims, "id_token": "the-id-token"}

    monkeypatch.setattr(router.client, "load_server_metadata", load_server_metadata)

    async def fetch_userinfo(token: dict) -> dict:
        assert userinfo is not None, "the userinfo endpoint was not expected to be asked"
        return userinfo

    monkeypatch.setattr(router.client, "authorize_access_token", authorize_access_token)
    monkeypatch.setattr(router.client, "userinfo", fetch_userinfo)

    app = FastAPI()
    add_exception_handlers(app)
    install_session(app, OIDC_CONFIG)
    install_users(app, users)
    app.include_router(router.router)
    app.state.auth_client = router.client
    return TestClient(app, raise_server_exceptions=False, follow_redirects=False)


def log_in(client: TestClient, return_to: str = "/#/communities/test"):
    client.get("/auth/login", params={"return_to": return_to})
    return client.get("/auth/callback")


# ── login ─────────────────────────────────────────────────────────────────


def test_login_sends_the_browser_to_the_identity_provider_with_pkce(data: Path, monkeypatch: pytest.MonkeyPatch):
    r = client_for(data, monkeypatch).get("/auth/login")

    assert r.status_code == 302
    location = urlparse(r.headers["location"])
    query = parse_qs(location.query)
    assert f"{location.scheme}://{location.netloc}{location.path}" == METADATA["authorization_endpoint"]
    assert query["client_id"] == ["cofy-management"]
    assert query["redirect_uri"] == ["http://testserver/auth/callback"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["openid profile email"]


def test_the_callback_logs_in_and_returns_to_where_the_login_started(data: Path, monkeypatch: pytest.MonkeyPatch):
    client = client_for(data, monkeypatch)

    r = log_in(client)

    assert r.status_code == 303
    assert r.headers["location"] == "/#/communities/test"
    assert client.get("/auth/me").json() == ANN


def test_the_session_cookie_is_http_only_and_same_site(data: Path, monkeypatch: pytest.MonkeyPatch):
    cookie = log_in(client_for(data, monkeypatch)).headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=lax" in cookie


def test_the_login_binds_the_waiting_grants(data: Path, monkeypatch: pytest.MonkeyPatch):
    log_in(client_for(data, monkeypatch))

    ann = stored_user(data, "ann@example.com")
    assert (ann["issuer"], ann["subject"]) == (ISSUER, "ann-sub")


def test_me_reports_no_community_to_someone_without_grants(data: Path, monkeypatch: pytest.MonkeyPatch):
    client = client_for(data, monkeypatch, sub="eve-sub", email="eve@example.com")

    log_in(client)

    assert client.get("/auth/me").json()["permissions"] == []


def test_the_login_binds_a_system_admin(data: Path, monkeypatch: pytest.MonkeyPatch):
    client = client_for(data, monkeypatch, sub="root-sub", email="root@example.com")

    log_in(client)

    me = client.get("/auth/me").json()
    assert me["system_admin"]
    assert [entry["slug"] for entry in me["permissions"]] == [None, "test"]
    assert all(len(entry["permissions"]) == 16 for entry in me["permissions"])
    assert stored_user(data, "root@example.com")["subject"] == "root-sub"


def test_an_unverified_email_is_logged_in_but_not_bound(data: Path, monkeypatch: pytest.MonkeyPatch):
    client = client_for(data, monkeypatch, email_verified=False)

    log_in(client)

    assert client.get("/auth/me").status_code == 200
    assert "subject" not in stored_user(data, "ann@example.com")


def test_an_email_missing_from_the_id_token_is_taken_from_userinfo(data: Path, monkeypatch: pytest.MonkeyPatch):
    userinfo = {"sub": "ann-sub", "email": "ann@example.com", "email_verified": "true", "name": "Ann"}
    client = client_for(data, monkeypatch, userinfo=userinfo)

    async def authorize_access_token(request) -> dict:
        return {"userinfo": {"iss": ISSUER, "sub": "ann-sub"}, "id_token": "the-id-token"}

    monkeypatch.setattr(client.app.state.auth_client, "authorize_access_token", authorize_access_token)

    log_in(client)

    assert client.get("/auth/me").json() == ANN


def test_userinfo_about_someone_else_is_ignored(data: Path, monkeypatch: pytest.MonkeyPatch):
    userinfo = {"sub": "eve-sub", "email": "eve@example.com", "email_verified": True}
    client = client_for(data, monkeypatch, userinfo=userinfo)

    async def authorize_access_token(request) -> dict:
        return {"userinfo": {"iss": ISSUER, "sub": "ann-sub"}, "id_token": "the-id-token"}

    monkeypatch.setattr(client.app.state.auth_client, "authorize_access_token", authorize_access_token)

    log_in(client)

    assert client.get("/auth/me").json()["email"] is None


@pytest.mark.parametrize(
    "return_to", ["https://evil.example/", "//evil.example/", "/\\evil.example", "javascript:alert(1)", ""]
)
def test_a_login_only_returns_to_this_site(return_to: str):
    assert safe_return_to(return_to) == "/"


def test_a_path_on_this_site_is_returned_to():
    assert safe_return_to("/#/communities/test") == "/#/communities/test"


# ── the session ───────────────────────────────────────────────────────────


def test_without_a_login_me_is_401(data: Path, monkeypatch: pytest.MonkeyPatch):
    r = client_for(data, monkeypatch).get("/auth/me")

    assert r.status_code == 401
    assert r.json()["code"] == "not-authenticated"


def test_a_session_ends_when_its_lifetime_is_up_even_while_in_use(data: Path, monkeypatch: pytest.MonkeyPatch):
    # Already over when it starts, while the cookie itself would still be kept for hours.
    expired = OIDC_CONFIG.model_copy(update={"session_lifetime": dt.timedelta(seconds=-1)})
    client = client_for(data, monkeypatch, expired)

    log_in(client)

    assert client.get("/auth/me").status_code == 401


# ── logout ────────────────────────────────────────────────────────────────


def test_logout_ends_the_session_and_the_identity_providers(data: Path, monkeypatch: pytest.MonkeyPatch):
    client = client_for(data, monkeypatch)
    log_in(client)

    r = client.post("/auth/logout")

    assert r.status_code == 303
    location = urlparse(r.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == METADATA["end_session_endpoint"]
    assert parse_qs(location.query)["id_token_hint"] == ["the-id-token"]
    assert client.get("/auth/me").status_code == 401


def test_logout_stays_here_when_the_identity_provider_has_no_end_session(data: Path, monkeypatch: pytest.MonkeyPatch):
    metadata = {key: value for key, value in METADATA.items() if key != "end_session_endpoint"}
    client = client_for(data, monkeypatch, metadata=metadata)

    assert client.post("/auth/logout").headers["location"] == "/"


def test_logout_ends_the_session_here_when_the_identity_provider_cannot_be_reached(
    data: Path, monkeypatch: pytest.MonkeyPatch
):
    client = client_for(data, monkeypatch)
    log_in(client)
    monkeypatch.setattr(client.app.state.auth_client, "load_server_metadata", _timing_out)

    r = client.post("/auth/logout")

    assert (r.status_code, r.headers["location"]) == (303, "/")
    assert client.get("/auth/me").status_code == 401


async def _timing_out() -> dict:
    raise httpx.ReadTimeout("the identity provider took too long")
