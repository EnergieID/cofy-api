"""The users file at login: who an identity is, and binding them at their first login."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cofy.management.auth.access import Role
from cofy.management.persitance.file.users import FileUsersPersistence

from ...access_fixture import ISSUER, identity


def users_file(tmp_path: Path, *users: dict) -> Path:
    path = tmp_path / "access" / "users.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"users": list(users)}))
    return path


def stored(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["users"]


def test_without_a_file_nobody_is_listed(tmp_path: Path):
    assert FileUsersPersistence(tmp_path / "missing.yaml").match(identity("admin")) is None


def test_a_file_listing_someone_twice_is_refused(tmp_path: Path):
    path = users_file(tmp_path, {"email": "ann@example.com"}, {"email": "ANN@example.com"})

    with pytest.raises(ValueError, match="ann@example.com"):
        FileUsersPersistence(path).match(identity("ann"))


def test_an_empty_file_is_refused_as_truncated(tmp_path: Path):
    path = tmp_path / "users.yaml"
    path.write_text("")

    with pytest.raises(ValueError, match="mapping"):
        FileUsersPersistence(path).match(identity("ann"))


# ── logging in ────────────────────────────────────────────────────────────


def test_matches_the_person_an_identity_is(tmp_path: Path):
    users = FileUsersPersistence(users_file(tmp_path, {"email": "admin@example.com", "system_admin": True}))

    found = users.match(identity("admin"))

    assert found is not None and found.system_admin
    assert users.match(identity("ann")) is None


def test_binding_writes_the_identity_into_the_file(tmp_path: Path):
    path = users_file(tmp_path, {"email": "admin@example.com", "system_admin": True}, {"email": "other@example.com"})

    FileUsersPersistence(path).bind(identity("admin"))

    assert stored(path) == [
        {"email": "admin@example.com", "issuer": ISSUER, "subject": "admin-sub", "system_admin": True},
        {"email": "other@example.com"},
    ]


def test_a_bound_person_stays_themselves_whatever_their_email_becomes(tmp_path: Path):
    path = users_file(tmp_path, {"email": "admin@example.com", "issuer": ISSUER, "subject": "admin-sub"})

    renamed = identity("admin").model_copy(update={"email": "new@example.com"})

    assert FileUsersPersistence(path).match(renamed) is not None


def test_binding_without_a_match_leaves_the_file_alone(tmp_path: Path):
    path = users_file(tmp_path, {"email": "admin@example.com", "grants": {"demo": Role.community_admin.value}})
    before = path.read_text()

    FileUsersPersistence(path).bind(identity("ann"))

    assert path.read_text() == before
