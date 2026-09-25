import asyncio
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from cofy.api.debug_middleware import DebugMiddleware


@pytest.fixture
def debug_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def app(debug_dir: Path) -> FastAPI:
    _app = FastAPI()
    _app.add_middleware(DebugMiddleware, debug_dir=debug_dir)

    @_app.get("/hello")
    def hello():
        return {"message": "hello"}

    return _app


def test_middleware_skips_debug_endpoints(app: FastAPI) -> None:
    """Requests to /debug/... paths are passed through without profiling."""
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/debug/some-id/profile")
    # Route does not exist (404), but no profiling headers must be added
    assert "X-Debug-Id" not in response.headers
    assert "X-Debug-Url" not in response.headers


def test_middleware_adds_debug_headers(app: FastAPI) -> None:
    client = TestClient(app)
    response = client.get("/hello")
    assert response.status_code == 200
    assert "X-Debug-Id" in response.headers
    assert "X-Debug-Url" in response.headers


def test_middleware_writes_profile(app: FastAPI, debug_dir: Path) -> None:
    client = TestClient(app)
    response = client.get("/hello")
    request_id = response.headers["X-Debug-Id"]
    profile_path = debug_dir / request_id / "profile.txt"
    assert profile_path.exists()
    assert len(profile_path.read_text(encoding="utf-8")) > 0


def test_middleware_debug_url_contains_request_id(app: FastAPI) -> None:
    client = TestClient(app)
    response = client.get("/hello")
    request_id = response.headers["X-Debug-Id"]
    debug_url = response.headers["X-Debug-Url"]
    assert request_id in debug_url
    assert debug_url.startswith("/debug/")


@pytest.mark.asyncio
async def test_concurrent_requests_produce_separate_profiles(debug_dir: Path) -> None:
    """Two overlapping requests must each get their own clean profile file."""
    _app = FastAPI()
    _app.add_middleware(DebugMiddleware, debug_dir=debug_dir)

    @_app.get("/slow")
    async def slow():
        await asyncio.sleep(0.05)
        return {"message": "slow"}

    async with AsyncClient(transport=ASGITransport(app=_app), base_url="http://test") as client:
        r1, r2 = await asyncio.gather(client.get("/slow"), client.get("/slow"))

    assert r1.status_code == 200
    assert r2.status_code == 200

    id1 = r1.headers["X-Debug-Id"]
    id2 = r2.headers["X-Debug-Id"]
    assert id1 != id2

    assert (debug_dir / id1 / "profile.txt").exists()
    assert (debug_dir / id2 / "profile.txt").exists()
