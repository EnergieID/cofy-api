import os
from pathlib import Path

from cofy.modules.members import Member, MembersFileSource


def _make_loader(members: dict[str, Member]):
    """Return a simple loader function that always returns the given dict."""

    def loader(path: Path) -> dict[str, Member]:
        return members

    return loader


def _write(path: Path, content: str = "x") -> None:
    """Write content to a file and nudge mtime to guarantee a new signature."""
    path.write_text(content)
    # Ensure mtime changes even on fast filesystems
    stat = path.stat()
    new_mtime = stat.st_mtime_ns + 1_000_000
    os.utime(path, ns=(new_mtime, new_mtime))


def test_members_file_source_loads_and_sorts_members(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    members = {
        "M002": Member(id="M002"),
        "M001": Member(id="M001"),
        "M003": Member(id="M003"),
    }
    source = MembersFileSource(str(file_path), _make_loader(members))

    result = source.list()
    assert [m.id for m in result] == ["M001", "M002", "M003"]


def test_members_file_source_paginates(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    members = {f"M{i:03d}": Member(id=f"M{i:03d}") for i in range(1, 6)}
    source = MembersFileSource(str(file_path), _make_loader(members), page_size=2)

    assert [m.id for m in source.list(page=1)] == ["M001", "M002"]
    assert [m.id for m in source.list(page=2)] == ["M003", "M004"]
    assert [m.id for m in source.list(page=3)] == ["M005"]
    assert source.list(page=4) == []


def test_members_file_source_get_by_id(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    m1 = Member(id="M001")
    m2 = Member(id="M002")
    source = MembersFileSource(str(file_path), _make_loader({"M001": m1, "M002": m2}))

    assert source.get("M001") is m1
    assert source.get("M002") is m2
    assert source.get("nonexistent") is None


def test_members_file_source_verify(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    m1 = Member(id="M001", activation_code="ACT-001")
    m2 = Member(id="M002", activation_code="ACT-002")
    source = MembersFileSource(str(file_path), _make_loader({"M001": m1, "M002": m2}))

    assert source.verify("ACT-001") is m1
    assert source.verify("ACT-002") is m2
    assert source.verify("nonexistent") is None
    # member ID alone is not a valid activation code
    assert source.verify("M001") is None


def test_members_file_source_verify_without_activation_code(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    m1 = Member(id="M001")  # no activation_code
    source = MembersFileSource(str(file_path), _make_loader({"M001": m1}))

    assert source.verify("M001") is None
    assert source.verify("") is None


def test_members_file_source_reloads_when_file_changes(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path, "v1")

    m1 = Member(id="M001")
    m2 = Member(id="M002")
    call_count = 0

    def counting_loader(path: Path) -> dict[str, Member]:
        nonlocal call_count
        call_count += 1
        return {"M001": m1} if call_count == 1 else {"M001": m1, "M002": m2}

    source = MembersFileSource(str(file_path), counting_loader)
    assert call_count == 1
    assert len(source.list()) == 1

    # Listing again without a file change should NOT trigger a reload
    source.list()
    assert call_count == 1

    # Changing the file should trigger a reload on the next list()
    _write(file_path, "v2")
    assert len(source.list()) == 2
    assert call_count == 2


def test_members_file_source_response_model_is_member(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path)

    source = MembersFileSource(str(file_path), _make_loader({}))

    assert source.response_model is Member


def test_members_file_source_does_not_reload_for_missing_file(tmp_path):
    file_path = tmp_path / "missing.txt"

    source = MembersFileSource(str(file_path), _make_loader({"M001": Member(id="M001")}))

    # File doesn't exist: initial load is skipped, list returns empty
    assert source.list() == []
    assert source.verify("M001") is None


def test_members_file_source_preserves_state_when_loader_raises(tmp_path):
    file_path = tmp_path / "members.txt"
    _write(file_path, "v1")

    m1 = Member(id="M001")
    call_count = 0

    def flaky_loader(path: Path) -> dict[str, Member]:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise ValueError("parse error")
        return {"M001": m1}

    source = MembersFileSource(str(file_path), flaky_loader)
    assert source.list() == [m1]

    # Trigger a reload with a failing loader — previous state should be retained
    _write(file_path, "v2")
    assert source.list() == [m1]
    assert call_count == 2


def test_members_file_source_no_double_reload_under_lock(tmp_path):
    """Inside the lock, _maybe_reload re-checks the signature so that a second
    thread that lost the race does not call the loader again."""
    file_path = tmp_path / "members.txt"
    _write(file_path, "v1")

    m1 = Member(id="M001")
    call_count = 0

    def counting_loader(path: Path) -> dict[str, Member]:
        nonlocal call_count
        call_count += 1
        return {"M001": m1}

    source = MembersFileSource(str(file_path), counting_loader)
    assert call_count == 1

    # Change the file so the outer signature check fails (reload looks needed)
    _write(file_path, "v2")

    # Simulate a concurrent thread having already reloaded: the second call to
    # _get_file_signature (inside the lock) updates the stored signature so the
    # inner guard detects there is nothing left to do.
    original_get_sig = source._get_file_signature
    inner_call = False

    def patched_get_sig():
        nonlocal inner_call
        sig = original_get_sig()
        if inner_call:
            # Pretend the other thread already persisted this signature
            source._file_signature = sig
        inner_call = True
        return sig

    source._get_file_signature = patched_get_sig  # type: ignore[method-assign]
    source.list()
    assert call_count == 1  # loader was not called a second time
