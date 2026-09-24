"""Tests for the console's static-file mount, which `main` sets up at import time from
`COFY_MANAGEMENT_STATIC_DIR` - nothing else in this suite imports the module, so each test
reimports it fresh under the environment it wants to observe."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _import_main(monkeypatch: pytest.MonkeyPatch, static_dir: Path | None):
    if static_dir is None:
        monkeypatch.delenv("COFY_MANAGEMENT_STATIC_DIR", raising=False)
    else:
        monkeypatch.setenv("COFY_MANAGEMENT_STATIC_DIR", str(static_dir))
    sys.modules.pop("cofy.management.main", None)
    return importlib.import_module("cofy.management.main")


def test_mounts_console_when_static_dir_is_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "index.html").write_text("<html>console</html>")

    main = _import_main(monkeypatch, tmp_path)
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert "console" in response.text


def test_no_console_mount_without_static_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    main = _import_main(monkeypatch, None)
    client = TestClient(main.app, raise_server_exceptions=False)

    response = client.get("/")

    assert response.status_code == 404
