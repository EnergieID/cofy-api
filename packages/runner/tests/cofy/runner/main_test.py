"""Tests for the runner's configuration from the environment, which `main` reads at import time."""

from __future__ import annotations

import datetime as dt
import importlib
import sys
from pathlib import Path

import pytest


def _import_main():
    sys.modules.pop("cofy.runner.main", None)
    return importlib.import_module("cofy.runner.main")


@pytest.fixture(autouse=True)
def directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("COFY_RUNNER_DIRECTORY", str(tmp_path))
    monkeypatch.delenv("COFY_RUNNER_COMMUNITIES", raising=False)
    monkeypatch.delenv("COFY_RUNNER_POLL_INTERVAL", raising=False)
    return tmp_path


def test_defaults(directory: Path):
    app = _import_main().app

    assert app.directory == directory
    assert app.communities is None
    assert app.poll_interval == dt.timedelta(seconds=2)


def test_communities_and_poll_interval(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COFY_RUNNER_COMMUNITIES", "demo, other,")
    monkeypatch.setenv("COFY_RUNNER_POLL_INTERVAL", "PT0.5S")

    app = _import_main().app

    assert app.communities == frozenset({"demo", "other"})
    assert app.poll_interval == dt.timedelta(milliseconds=500)


def test_does_not_start_without_a_directory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("COFY_RUNNER_DIRECTORY")

    with pytest.raises(RuntimeError, match="COFY_RUNNER_DIRECTORY"):
        _import_main()


@pytest.mark.parametrize("interval", ["2 seconds", "P1M", "PT0S"])
def test_does_not_start_with_an_unusable_poll_interval(monkeypatch: pytest.MonkeyPatch, interval: str):
    monkeypatch.setenv("COFY_RUNNER_POLL_INTERVAL", interval)

    with pytest.raises(RuntimeError, match="COFY_RUNNER_POLL_INTERVAL"):
        _import_main()
