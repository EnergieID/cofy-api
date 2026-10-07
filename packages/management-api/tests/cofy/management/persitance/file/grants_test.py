"""Grants, as kept in the users file with the people they are granted to."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from cofy.management.auth.access import Grant, Role
from cofy.management.errors import ResourceAlreadyExistsError, ResourceNotFoundError
from cofy.management.persitance.file.grants import FileGrantsPersistence

from ...access_fixture import ISSUER

ADMIN = Role.community_admin


def users_file(tmp_path: Path, *users: dict) -> Path:
    path = tmp_path / "access" / "users.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"users": list(users)}))
    return path


def stored(path: Path) -> list[dict]:
    return yaml.safe_load(path.read_text())["users"]


def grant(email: str = "ann@example.com") -> Grant:
    return Grant(email=email, role=ADMIN)


def test_lists_the_grants_in_a_community_with_whether_their_person_logged_in(tmp_path: Path):
    path = users_file(
        tmp_path,
        {"email": "ann@example.com", "issuer": ISSUER, "subject": "ann-sub", "grants": {"test": "community_admin"}},
        {"email": "bob@example.com", "grants": {"test": "community_admin", "other": "community_admin"}},
        {"email": "cas@example.com", "grants": {"other": "community_admin"}},
    )

    assert FileGrantsPersistence(path).all("test") == [
        Grant(email="ann@example.com", role=ADMIN, bound=True),
        Grant(email="bob@example.com", role=ADMIN, bound=False),
    ]


def test_the_first_grant_creates_the_file(tmp_path: Path):
    path = tmp_path / "access" / "users.yaml"

    FileGrantsPersistence(path).create("test", grant())

    assert stored(path) == [{"email": "ann@example.com", "grants": {"test": "community_admin"}}]


def test_a_grant_in_another_community_is_added_to_the_same_person(tmp_path: Path):
    path = users_file(tmp_path, {"email": "ann@example.com", "grants": {"test": "community_admin"}})

    FileGrantsPersistence(path).create("other", grant("ANN@example.com"))

    assert stored(path) == [
        {"email": "ann@example.com", "grants": {"test": "community_admin", "other": "community_admin"}}
    ]


def test_granting_twice_in_one_community_fails(tmp_path: Path):
    grants = FileGrantsPersistence(tmp_path / "users.yaml")
    grants.create("test", grant())

    with pytest.raises(ResourceAlreadyExistsError):
        grants.create("test", grant("Ann@Example.com"))


def test_a_grant_someone_does_not_have_is_not_found(tmp_path: Path):
    path = users_file(tmp_path, {"email": "ann@example.com", "grants": {"test": "community_admin"}})

    with pytest.raises(ResourceNotFoundError):
        FileGrantsPersistence(path).get("other", "ann@example.com")
    with pytest.raises(ResourceNotFoundError):
        FileGrantsPersistence(path).delete("test", "bob@example.com")


def test_replacing_keeps_the_binding(tmp_path: Path):
    ann = {"email": "ann@example.com", "issuer": ISSUER, "subject": "ann-sub", "grants": {"test": "community_admin"}}
    path = users_file(tmp_path, ann)

    replaced = FileGrantsPersistence(path).replace("test", "ann@example.com", grant())

    assert replaced.bound
    assert stored(path) == [ann]


def test_deleting_someones_last_grant_forgets_them(tmp_path: Path):
    path = users_file(tmp_path, {"email": "ann@example.com", "grants": {"test": "community_admin"}})

    FileGrantsPersistence(path).delete("test", "ann@example.com")

    assert stored(path) == []


def test_deleting_keeps_a_system_admin_listed(tmp_path: Path):
    path = users_file(
        tmp_path, {"email": "admin@example.com", "system_admin": True, "grants": {"test": "community_admin"}}
    )

    FileGrantsPersistence(path).delete("test", "admin@example.com")

    assert stored(path) == [{"email": "admin@example.com", "system_admin": True}]


def test_deleting_all_grants_in_a_community_leaves_the_others(tmp_path: Path):
    path = users_file(
        tmp_path,
        {"email": "ann@example.com", "grants": {"test": "community_admin", "other": "community_admin"}},
        {"email": "bob@example.com", "grants": {"test": "community_admin"}},
    )

    FileGrantsPersistence(path).delete_all("test")

    assert stored(path) == [{"email": "ann@example.com", "grants": {"other": "community_admin"}}]
