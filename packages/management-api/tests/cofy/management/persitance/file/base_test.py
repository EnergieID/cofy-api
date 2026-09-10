"""Tests for FilePersistence._open_community_config's locking behaviour.

These are deliberately lower-level than the HTTP-integration tests in
tests/cofy/management/api/modules_test.py: they prove the locking mechanism itself
(held for the whole block, released either way, reads and writes correctly excluding
each other while not needlessly excluding one another, and a real concurrent write race
resolved correctly), rather than exercising it incidentally through the API.
"""

from __future__ import annotations

import fcntl
import threading
import time
from pathlib import Path

import pytest
import yaml
from cofy.api.cofy_api import CofyAPISettings
from cofy.modules.billing import BillingModuleSettings
from yaml.representer import RepresenterError

from cofy.management.errors import ResourceAlreadyExistsError
from cofy.management.persitance.file.base import (
    DATA_DIR_ENV_VAR,
    PACKAGED_BASE_PATH,
    default_base_path,
)
from cofy.management.persitance.file.modules import FileModulesPersistence


@pytest.fixture()
def tmp_data(tmp_path: Path) -> Path:
    community = {"type": "cofy_api", "modules": [{"type": "billing", "name": "default"}]}
    (tmp_path / "test.yaml").write_text(yaml.safe_dump(community))
    return tmp_path


def _exclusive_lock_is_held(path: Path) -> bool:
    """True if some other file handle currently holds any lock (shared or exclusive) that
    conflicts with acquiring an exclusive lock ourselves."""
    with path.open("r") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        else:
            fcntl.flock(probe, fcntl.LOCK_UN)
            return False


# ── write mode: exclusive lock, save on clean exit only ───────────────────


def test_write_lock_is_held_for_the_whole_block_and_released_on_clean_exit(tmp_data: Path):
    persistence = FileModulesPersistence(tmp_data)
    path = tmp_data / "test.yaml"

    assert not _exclusive_lock_is_held(path)

    with persistence._open_community_config("test", "write") as config:
        assert _exclusive_lock_is_held(path)
        assert config.modules  # just touching it - it doesn't need to be mutated

    assert not _exclusive_lock_is_held(path)


def test_write_lock_is_released_when_the_block_raises(tmp_data: Path):
    persistence = FileModulesPersistence(tmp_data)
    path = tmp_data / "test.yaml"

    with pytest.raises(ValueError, match="boom"), persistence._open_community_config("test", "write") as config:
        assert _exclusive_lock_is_held(path)
        _ = config
        raise ValueError("boom")

    assert not _exclusive_lock_is_held(path)


def test_nothing_is_written_when_the_write_block_raises(tmp_data: Path):
    persistence = FileModulesPersistence(tmp_data)
    path = tmp_data / "test.yaml"
    before = path.read_bytes()

    with pytest.raises(ResourceAlreadyExistsError):
        persistence.create("test", BillingModuleSettings(name="default"))  # already exists

    assert path.read_bytes() == before


def test_concurrent_creates_of_the_same_module_do_not_race(tmp_data: Path, monkeypatch: pytest.MonkeyPatch):
    """Without locking, two concurrent creates of the same module could both read the
    config before either writes - both then see no duplicate and both write, the second
    write silently clobbering the first's. To force that overlap deterministically (rather
    than trusting that two fast local calls happen not to race), the first call is paused
    *after* it has parsed its config - so it is holding stale, pre-mutation data, exactly
    as it would if genuinely preempted at that point - until the second call has run to
    completion. The pause is placed after parsing rather than during the file read itself,
    since pausing mid-read would let the delayed read pick up the second call's already-
    written result and mask the race instead of reproducing it.
    """
    persistence = FileModulesPersistence(tmp_data)
    original_validate = CofyAPISettings.model_validate

    calls: list[int] = []
    calls_lock = threading.Lock()
    first_call_entered = threading.Event()
    release_first_call = threading.Event()

    def instrumented_validate(data):
        result = original_validate(data)  # parse first, so `first` holds a real, stale config
        with calls_lock:
            calls.append(1)
            is_first = len(calls) == 1
        if is_first:
            first_call_entered.set()
            assert release_first_call.wait(timeout=5), "second call never completed"
        return result

    monkeypatch.setattr(CofyAPISettings, "model_validate", instrumented_validate)

    results: dict[str, str] = {}

    def attempt(key: str) -> None:
        try:
            persistence.create("test", BillingModuleSettings(name="race"))
            results[key] = "created"
        except ResourceAlreadyExistsError:
            results[key] = "conflict"

    first = threading.Thread(target=attempt, args=("first",))
    first.start()
    assert first_call_entered.wait(timeout=5), "first call never reached its critical section"

    second = threading.Thread(target=attempt, args=("second",))
    second.start()

    # Give the second call a chance to run: under the (buggy) unlocked behaviour it would
    # complete almost immediately here, which is exactly the race being guarded against;
    # under the fixed, locked behaviour it instead blocks on the lock the first call is
    # still holding, and does not proceed until the first call is released below.
    time.sleep(0.3)
    release_first_call.set()

    first.join(timeout=5)
    second.join(timeout=5)

    assert sorted(results.values()) == ["conflict", "created"]
    saved = yaml.safe_load((tmp_data / "test.yaml").read_text())["modules"]
    assert sum(1 for m in saved if m["type"] == "billing" and m["name"] == "race") == 1


# ── read mode: shared lock, never saves ────────────────────────────────────


def test_read_mode_does_not_persist_mutations_to_the_yielded_config(tmp_data: Path):
    persistence = FileModulesPersistence(tmp_data)
    path = tmp_data / "test.yaml"
    before = path.read_bytes()

    with persistence._open_community_config("test", "read") as config:
        config.modules = config.modules + [BillingModuleSettings(name="should-not-be-saved")]

    assert path.read_bytes() == before


def test_concurrent_reads_do_not_block_each_other(tmp_data: Path):
    """Two reads must be able to proceed at the same time - only a write should exclude
    them, not another read - otherwise every GET would needlessly serialize against every
    other GET."""
    persistence = FileModulesPersistence(tmp_data)

    first_reader_inside = threading.Event()
    let_first_reader_finish = threading.Event()

    def slow_reader() -> None:
        with persistence._open_community_config("test", "read"):
            first_reader_inside.set()
            let_first_reader_finish.wait(timeout=5)

    reader_thread = threading.Thread(target=slow_reader)
    reader_thread.start()
    assert first_reader_inside.wait(timeout=5)

    # A second read must be able to acquire its (shared) lock and complete right away,
    # without waiting for the first reader still holding the file open.
    second_read_completed = threading.Event()

    def second_reader() -> None:
        with persistence._open_community_config("test", "read"):
            pass
        second_read_completed.set()

    second_reader_thread = threading.Thread(target=second_reader)
    second_reader_thread.start()
    second_reader_thread.join(timeout=2)

    assert second_read_completed.is_set(), "a second read blocked behind an in-progress read"

    let_first_reader_finish.set()
    reader_thread.join(timeout=5)


def test_read_waits_for_an_in_progress_write_instead_of_seeing_a_torn_file(
    tmp_data: Path, monkeypatch: pytest.MonkeyPatch
):
    """The write path truncates the file before rewriting it, so a read landing in that
    window (if it weren't excluded) would see an empty/partial file instead of either the
    old or the new content. A read must instead wait for the write to finish.

    The writer is paused at its serialization step, which is inside the locked block and
    just ahead of the truncate, so the reader below is genuinely contending for a lock the
    writer still holds."""
    persistence = FileModulesPersistence(tmp_data)
    original_dump = yaml.safe_dump

    writer_is_committing = threading.Event()
    let_writer_finish = threading.Event()

    def instrumented_dump(data, **kwargs):
        writer_is_committing.set()
        assert let_writer_finish.wait(timeout=5), "reader never attempted to read"
        return original_dump(data, **kwargs)

    monkeypatch.setattr(yaml, "safe_dump", instrumented_dump)

    def writer() -> None:
        with persistence._open_community_config("test", "write") as config:
            config.modules = config.modules + [BillingModuleSettings(name="new")]

    writer_thread = threading.Thread(target=writer)
    writer_thread.start()
    assert writer_is_committing.wait(timeout=5), "writer never reached its commit step"

    reader_result: dict[str, list[str]] = {}

    def reader() -> None:
        with persistence._open_community_config("test", "read") as config:
            reader_result["names"] = [m.name for m in config.modules]

    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    time.sleep(0.2)  # give the reader a real chance to attempt (and block on) the lock

    assert "names" not in reader_result, "read proceeded while the file was mid-write"

    let_writer_finish.set()
    writer_thread.join(timeout=5)
    reader_thread.join(timeout=5)

    # The reader must see the complete, final write - not a torn, in-between file.
    assert reader_result["names"] == ["default", "new"]


def test_a_failed_serialization_leaves_the_file_intact(tmp_data: Path, monkeypatch: pytest.MonkeyPatch):
    """The config is serialized before the file is truncated, so a dump that raises must not
    destroy the previous contents - truncating first would leave an empty config behind."""
    persistence = FileModulesPersistence(tmp_data)
    path = tmp_data / "test.yaml"
    before = path.read_bytes()

    def exploding_dump(data, **kwargs):
        raise RepresenterError("cannot represent an object")

    monkeypatch.setattr(yaml, "safe_dump", exploding_dump)

    with pytest.raises(RepresenterError):
        persistence.create("test", BillingModuleSettings(name="new"))

    assert path.read_bytes() == before


# ── slug safety: defense in depth ─────────────────────────────────────────


@pytest.mark.parametrize("slug", ["../outside", "a/b", ".", "..", "", "with space"])
def test_community_path_refuses_a_slug_that_is_not_a_safe_filename(tmp_data: Path, slug: str):
    """Called directly - bypassing the routers' own pattern checks - the layer that turns a
    slug into a filename must still refuse anything that could address another directory."""
    persistence = FileModulesPersistence(tmp_data)

    with pytest.raises(ValueError, match="must match"):
        persistence._community_path(slug)


def test_community_path_accepts_the_documented_slug_characters(tmp_data: Path):
    persistence = FileModulesPersistence(tmp_data)

    assert persistence._community_path("Abc-123_x") == tmp_data / "Abc-123_x.yaml"


# ── where the data directory comes from ───────────────────────────────────


def test_data_directory_defaults_to_the_packaged_samples(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(DATA_DIR_ENV_VAR, raising=False)

    assert default_base_path() == PACKAGED_BASE_PATH


def test_data_directory_can_be_configured(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """A deployment that creates communities must be able to point this somewhere writable -
    the packaged path lives inside the installed distribution."""
    monkeypatch.setenv(DATA_DIR_ENV_VAR, str(tmp_path))

    assert default_base_path() == tmp_path
    assert FileModulesPersistence().base_path == tmp_path
