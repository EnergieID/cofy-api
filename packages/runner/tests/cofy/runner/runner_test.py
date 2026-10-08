"""Tests for CommunityRunner: what it serves for each settings file, and what it serves once that file changes."""

from __future__ import annotations

import asyncio
import datetime as dt
import time
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from cofy.runner import CommunityRunner


def write(directory: Path, slug: str, settings: dict) -> None:
    """Replaced as the management API replaces it, so the change shows even within one clock tick."""
    staged = directory / f".{slug}.yaml.tmp"
    staged.write_text(yaml.safe_dump(settings))
    staged.replace(directory / f"{slug}.yaml")


def community(revision: int, title: str = "Demo") -> dict:
    return {
        "type": "cofy_api",
        "title": title,
        "revision": revision,
        "modules": [{"type": "billing", "name": "default"}],
    }


BROKEN = {"type": "cofy_api", "modules": [{"type": "no_such_module", "name": "x"}]}


def refreshed(runner: CommunityRunner) -> TestClient:
    asyncio.run(runner.refresh())
    return TestClient(runner)


def test_serves_each_community_under_its_slug(tmp_path: Path):
    write(tmp_path, "demo", community(1, "Demo"))
    write(tmp_path, "other", community(4, "Other"))
    client = refreshed(CommunityRunner(tmp_path))

    demo = client.get("/demo/openapi.json").json()
    other = client.get("/other/openapi.json").json()

    assert (demo["info"]["title"], demo["info"]["version"].split("+")[1]) == ("Demo", "1")
    assert (other["info"]["title"], other["info"]["version"].split("+")[1]) == ("Other", "4")
    assert demo["servers"] == [{"url": "/demo"}]
    assert list(demo["paths"]) == ["/billing/default/v2"]


def test_health_is_the_communitys_own(tmp_path: Path):
    write(tmp_path, "demo", community(3))
    client = refreshed(CommunityRunner(tmp_path))

    r = client.get("/demo/health")

    assert (r.status_code, r.json()) == (200, {"status": "ok", "revision": 3})


def test_a_change_is_built_and_swapped_in(tmp_path: Path):
    write(tmp_path, "demo", community(1, "Before"))
    runner = CommunityRunner(tmp_path)
    client = refreshed(runner)

    write(tmp_path, "demo", community(2, "After"))
    asyncio.run(runner.refresh())

    assert client.get("/demo/health").json() == {"status": "ok", "revision": 2}
    assert client.get("/demo/openapi.json").json()["info"]["title"] == "After"


def test_an_unchanged_file_is_not_built_again(tmp_path: Path):
    write(tmp_path, "demo", community(1))
    runner = CommunityRunner(tmp_path)
    asyncio.run(runner.refresh())
    built = runner.community("demo")

    asyncio.run(runner.refresh())

    assert runner.community("demo") is built


def test_settings_that_fail_keep_the_previous_api_serving(tmp_path: Path):
    write(tmp_path, "demo", community(1, "Working"))
    runner = CommunityRunner(tmp_path)
    client = refreshed(runner)

    write(tmp_path, "demo", BROKEN)
    asyncio.run(runner.refresh())

    assert client.get("/demo/health").json() == {"status": "ok", "revision": 1}
    assert client.get("/demo/openapi.json").json()["info"]["title"] == "Working"


def test_fixed_settings_are_current_again(tmp_path: Path):
    write(tmp_path, "demo", community(1))
    runner = CommunityRunner(tmp_path)
    client = refreshed(runner)
    write(tmp_path, "demo", BROKEN)
    asyncio.run(runner.refresh())

    write(tmp_path, "demo", community(3))
    asyncio.run(runner.refresh())

    assert client.get("/demo/health").json() == {"status": "ok", "revision": 3}


@pytest.mark.parametrize("content", [yaml.safe_dump(BROKEN), "", "modules: [unclosed"])
def test_settings_that_never_built_are_unavailable(tmp_path: Path, content: str, caplog: pytest.LogCaptureFixture):
    (tmp_path / "demo.yaml").write_text(content)
    client = refreshed(CommunityRunner(tmp_path))

    health = client.get("/demo/health")

    assert health.status_code == 503
    assert client.get("/demo/openapi.json").status_code == 503
    assert "'demo' failed to build" in caplog.text


def test_one_broken_community_leaves_the_others_alone(tmp_path: Path):
    write(tmp_path, "broken", BROKEN)
    write(tmp_path, "demo", community(1))
    client = refreshed(CommunityRunner(tmp_path))

    assert client.get("/demo/health").json() == {"status": "ok", "revision": 1}


def test_a_removed_community_is_no_longer_served(tmp_path: Path):
    write(tmp_path, "demo", community(1))
    runner = CommunityRunner(tmp_path)
    client = refreshed(runner)

    (tmp_path / "demo.yaml").unlink()
    asyncio.run(runner.refresh())

    assert client.get("/demo/health").status_code == 404
    assert client.get("/demo/openapi.json").status_code == 404


def test_an_unknown_community_is_not_found(tmp_path: Path):
    client = refreshed(CommunityRunner(tmp_path))

    assert client.get("/nope/health").status_code == 404
    assert client.get("/nope/openapi.json").status_code == 404


def test_only_the_listed_communities_are_served(tmp_path: Path):
    write(tmp_path, "demo", community(1))
    write(tmp_path, "other", community(1))
    client = refreshed(CommunityRunner(tmp_path, communities=frozenset({"other"})))

    assert client.get("/demo/health").status_code == 404
    assert client.get("/other/health").status_code == 200


def test_files_other_than_settings_are_ignored(tmp_path: Path):
    write(tmp_path, "demo", community(1))
    (tmp_path / ".demo.yaml.lock").write_text("")
    (tmp_path / "notes.txt").write_text("")
    runner = CommunityRunner(tmp_path)

    asyncio.run(runner.refresh())

    assert runner.community("demo") is not None
    assert runner.community(".demo.yaml") is None
    assert runner.community("notes") is None


def test_serving_builds_every_community_and_keeps_checking_for_changes(tmp_path: Path):
    write(tmp_path, "demo", community(1))

    with TestClient(CommunityRunner(tmp_path, poll_interval=dt.timedelta(milliseconds=20))) as client:
        assert client.get("/demo/health").json()["revision"] == 1

        write(tmp_path, "demo", community(2))
        deadline = time.monotonic() + 5
        while client.get("/demo/health").json()["revision"] != 2:
            assert time.monotonic() < deadline, "the change was never picked up"
            time.sleep(0.02)
