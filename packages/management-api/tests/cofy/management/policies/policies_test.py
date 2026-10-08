"""Who may do what: the policy's rules on each subject, for each kind of user."""

from __future__ import annotations

import pytest
from starlette.requests import Request

from cofy.management.auth.access import Role, Subject
from cofy.management.auth.user import User
from cofy.management.policies.community import CommunityPolicy
from cofy.management.policies.policy import Policy

from ..access_fixture import identity, user

RULES = ("all", "get", "create", "put", "delete")
EVERYTHING = set(RULES)
INSIDE_A_COMMUNITY = [Subject.modules, Subject.resources, Subject.secrets, Subject.tokens, Subject.grants]
ALLOWED_TYPES = [Subject.allowed_modules, Subject.allowed_resources]


@pytest.fixture()
def users() -> dict[str, User]:
    return {
        "system_admin": user("admin", system_admin=True),
        "admin_of_a": user("ann", grants={"a": Role.community_admin}),
        "admin_of_b": user("bob", grants={"b": Role.community_admin}),
        "nobody": User(identity("nobody"), None),
    }


def request(slug: str | None = "a") -> Request:
    return Request({"type": "http", "path_params": {} if slug is None else {"slug": slug}})


def allowed(user: User, subject: Subject, slug: str | None = "a", policy: type[Policy] = Policy) -> set[str]:
    instance = policy(user, request(slug), subject)
    return {rule for rule in RULES if instance.allows(getattr(policy, rule))}


# ── things inside a community ─────────────────────────────────────────────


@pytest.mark.parametrize("subject", INSIDE_A_COMMUNITY + ALLOWED_TYPES)
def test_a_system_admin_may_do_anything(subject: Subject, users: dict[str, User]):
    assert allowed(users["system_admin"], subject) == EVERYTHING


@pytest.mark.parametrize("subject", INSIDE_A_COMMUNITY)
def test_a_community_admin_may_do_anything_in_their_community(subject: Subject, users: dict[str, User]):
    assert allowed(users["admin_of_a"], subject) == EVERYTHING


@pytest.mark.parametrize("subject", INSIDE_A_COMMUNITY + ALLOWED_TYPES)
def test_a_community_admin_may_do_nothing_in_another_community(subject: Subject, users: dict[str, User]):
    assert allowed(users["admin_of_b"], subject) == set()


@pytest.mark.parametrize("subject", INSIDE_A_COMMUNITY + ALLOWED_TYPES)
def test_someone_without_grants_may_do_nothing(subject: Subject, users: dict[str, User]):
    assert allowed(users["nobody"], subject) == set()


def test_nobody_but_a_system_admin_may_do_anything_in_a_community_that_does_not_exist(users: dict[str, User]):
    assert allowed(users["admin_of_a"], Subject.modules, "missing") == set()
    assert allowed(users["system_admin"], Subject.modules, "missing") == EVERYTHING


@pytest.mark.parametrize("subject", ALLOWED_TYPES)
def test_a_community_admin_may_see_but_not_set_the_allowed_types(subject: Subject, users: dict[str, User]):
    assert allowed(users["admin_of_a"], subject) == {"all", "get"}


# ── communities ───────────────────────────────────────────────────────────


def community(user: User, slug: str | None = "a") -> set[str]:
    return allowed(user, Subject.community, slug, CommunityPolicy)


def test_listing_communities_takes_being_able_to_see_one(users: dict[str, User]):
    assert "all" not in community(users["nobody"], None)
    assert "all" in community(users["admin_of_a"], None)


def test_only_a_system_admin_may_create_a_community(users: dict[str, User]):
    assert "create" not in community(users["admin_of_a"], None)
    assert "create" in community(users["system_admin"], None)


def test_a_grant_left_in_a_deleted_community_lists_nothing(users: dict[str, User]):
    # Listing is allowed, and the listing itself is scoped to what exists and may be seen.
    stale = user("eve", grants={"gone": Role.community_admin})

    assert "all" in community(stale, None)
    assert CommunityPolicy.scope(stale, ["a", "b"]) == []


# Listing and creating are on routes without a slug, so only these three are ever asked about one community.
ON_ONE_COMMUNITY = {"get", "put", "delete"}


def test_a_community_admin_may_see_and_edit_but_not_delete_their_community(users: dict[str, User]):
    assert ON_ONE_COMMUNITY & community(users["admin_of_a"]) == {"get", "put"}


def test_a_system_admin_may_delete_a_community(users: dict[str, User]):
    assert ON_ONE_COMMUNITY & community(users["system_admin"]) == ON_ONE_COMMUNITY


def test_someone_without_grants_may_not_open_a_community(users: dict[str, User]):
    assert ON_ONE_COMMUNITY & community(users["nobody"]) == set()


def test_the_listing_is_scoped_to_the_communities_a_user_may_see(users: dict[str, User]):
    assert CommunityPolicy.scope(users["system_admin"], ["a", "b"]) == ["a", "b"]
    assert CommunityPolicy.scope(users["admin_of_a"], ["a", "b"]) == ["a"]
    assert CommunityPolicy.scope(users["nobody"], ["a", "b"]) == []


# ── the policy itself ─────────────────────────────────────────────────────


def test_a_rule_about_a_subject_fails_on_a_router_without_one(users: dict[str, User]):
    with pytest.raises(ValueError, match="subject"):
        Policy(users["admin_of_a"], request(), None).allows(Policy.get)


def test_a_system_admin_is_let_through_every_rule_even_one_that_refuses_everyone(users: dict[str, User]):
    def refuse(_: object) -> bool:
        return False

    assert Policy(users["system_admin"], request(), Subject.modules).allows(refuse)
    assert not Policy(users["admin_of_a"], request(), Subject.modules).allows(refuse)
