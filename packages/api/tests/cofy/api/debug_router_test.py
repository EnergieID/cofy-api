from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cofy.api.debug_router import DebugRouter


@pytest.fixture
def debug_dir(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(debug_dir: Path) -> TestClient:
    app = FastAPI()
    app.include_router(DebugRouter(debug_dir=debug_dir))
    return TestClient(app, raise_server_exceptions=False)


def test_get_profile_request_not_found(client: TestClient) -> None:
    response = client.get("/debug/nonexistent-id/profile")
    assert response.status_code == 404
    assert "nonexistent-id" in response.json()["detail"]


def test_get_profile_no_profile_file(client: TestClient, debug_dir: Path) -> None:
    request_id = "abc123"
    (debug_dir / request_id).mkdir()
    response = client.get(f"/debug/{request_id}/profile")
    assert response.status_code == 404
    assert "No profile data" in response.json()["detail"]


def test_get_profile_success(client: TestClient, debug_dir: Path) -> None:
    request_id = "abc123"
    request_dir = debug_dir / request_id
    request_dir.mkdir()
    (request_dir / "profile.txt").write_text("profile output", encoding="utf-8")
    response = client.get(f"/debug/{request_id}/profile")
    assert response.status_code == 200
    assert response.text == "profile output"
