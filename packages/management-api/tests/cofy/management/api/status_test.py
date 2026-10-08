"""Tests for StatusRouter: the runner's health of a community's API, against the revision saved for it."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.management.api.status import StatusRouter
from cofy.management.community_api import CommunityApi
from cofy.management.errors import add_exception_handlers
from cofy.management.persitance.file.communities import FileCommunitiesPersistence

from ..access_fixture import log_in_as_system_admin

STATUS = "/management/communities/test/status"


def client_for(tmp_path: Path, api: httpx.MockTransport) -> TestClient:
    (tmp_path / "test.yaml").write_text(yaml.safe_dump({"type": "cofy_api", "revision": 3}))
    app = FastAPI()
    add_exception_handlers(app)
    log_in_as_system_admin(app)
    client = CommunityApi(httpx.Client(base_url="https://cofy.example/communities", transport=api))
    app.include_router(StatusRouter(FileCommunitiesPersistence(tmp_path), client).router)
    return TestClient(app, raise_server_exceptions=False)


def answering(status_code: int, body: dict | None = None) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://cofy.example/communities/test/health"
        return httpx.Response(status_code, json=body)

    return httpx.MockTransport(handler)


def unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("refused", request=request)


@pytest.mark.parametrize(
    ("api", "state", "running_revision"),
    [
        (answering(200, {"status": "ok", "revision": 3}), "live", 3),
        (answering(200, {"status": "ok", "revision": 2}), "pending", 2),
        (answering(404, {"detail": "Not Found"}), "pending", None),
        (answering(503, {"detail": "Service Unavailable"}), "unavailable", None),
        (answering(200, {"unexpected": True}), "unavailable", None),
        (answering(500, {"detail": "Internal Server Error"}), "unavailable", None),
        (httpx.MockTransport(unreachable), "unavailable", None),
    ],
)
def test_state(tmp_path: Path, api: httpx.MockTransport, state: str, running_revision: int | None):
    r = client_for(tmp_path, api).get(STATUS)

    assert r.status_code == 200
    assert r.json() == {"state": state, "revision": 3, "running_revision": running_revision}


def test_an_unknown_community_is_not_found(tmp_path: Path):
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("the API of a community that doesn't exist was asked")

    r = client_for(tmp_path, httpx.MockTransport(never)).get("/management/communities/missing/status")

    assert r.status_code == 404
