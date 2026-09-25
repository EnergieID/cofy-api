"""Tests for FileCommunitiesPersistence.delete()'s locking - proving two concurrent (or
duplicated/retried) deletes of the same slug serialize instead of racing each other's unlink.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest
import yaml

from cofy.management.errors import ResourceNotFoundError
from cofy.management.persitance.file.communities import FileCommunitiesPersistence


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    (tmp_path / "test.yaml").write_text(yaml.safe_dump({"type": "cofy_api", "modules": []}))
    return tmp_path


def test_concurrent_deletes_of_the_same_community_do_not_race(tmp_data: Path, monkeypatch: pytest.MonkeyPatch):
    """Without the exclusive lock held across the unlink, both requests could pass the
    existence check before either one deletes the file - the second `unlink` then raises a
    raw, uncaught FileNotFoundError instead of the idempotent not-found this is meant to look
    like. The first call is paused right after it acquires the lock, immediately before its
    own unlink, forcing the second call to genuinely contend for the lock rather than trusting
    two fast local calls not to race.
    """
    persistence = FileCommunitiesPersistence(tmp_data)
    original_unlink = Path.unlink

    calls: list[int] = []
    calls_lock = threading.Lock()
    first_call_entered = threading.Event()
    release_first_call = threading.Event()

    def instrumented_unlink(self, *args, **kwargs):
        with calls_lock:
            calls.append(1)
            is_first = len(calls) == 1
        if is_first:
            first_call_entered.set()
            assert release_first_call.wait(timeout=5), "second call never completed"
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", instrumented_unlink)

    results: dict[str, str] = {}

    def attempt(key: str) -> None:
        try:
            persistence.delete("test")
            results[key] = "deleted"
        except ResourceNotFoundError:
            results[key] = "not-found"

    first = threading.Thread(target=attempt, args=("first",))
    first.start()
    assert first_call_entered.wait(timeout=5), "first call never reached its critical section"

    second = threading.Thread(target=attempt, args=("second",))
    second.start()

    # Give the second call a chance to run: under the (buggy) unlocked-during-unlink
    # behaviour it would complete almost immediately here, which is exactly the race being
    # guarded against; under the fixed, locked behaviour it instead blocks on the lock the
    # first call is still holding, and does not proceed until the first call is released below.
    time.sleep(0.3)
    release_first_call.set()

    first.join(timeout=5)
    second.join(timeout=5)

    assert sorted(results.values()) == ["deleted", "not-found"]
    assert not (tmp_data / "test.yaml").exists()
