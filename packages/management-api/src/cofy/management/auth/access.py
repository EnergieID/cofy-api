"""Who may do what in the management API: the permissions there are, the roles carrying them, and the people they
are granted to."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, model_validator


class Action(StrEnum):
    """What may be done to a subject: seeing it, or changing it (creating, updating and deleting alike)."""

    read = "read"
    write = "write"


class Subject(StrEnum):
    """A part of a community that permissions are given on."""

    community = "community"
    modules = "modules"
    resources = "resources"
    secrets = "secrets"
    grants = "grants"
    allowed_modules = "allowed_modules"
    allowed_resources = "allowed_resources"


class Permission(BaseModel):
    """An action on a subject of a community."""

    model_config = ConfigDict(frozen=True)

    action: Action
    subject: Subject

    @classmethod
    def all(cls) -> list[Permission]:
        """Every action on every subject, by subject and then action, in the order they are declared."""
        return [cls(action=action, subject=subject) for subject in Subject for action in Action]


class Role(StrEnum):
    """A named set of permissions, granted to a person on a community."""

    community_admin = "community_admin"


ROLE_PERMISSIONS: Mapping[Role, frozenset[Permission]] = {
    # Everything in their community, except changing which types it may use.
    Role.community_admin: frozenset(Permission.all())
    - {
        Permission(action=Action.write, subject=Subject.allowed_modules),
        Permission(action=Action.write, subject=Subject.allowed_resources),
    },
}
"""The permissions each role carries, the only place a role turns into what it allows."""


class Identity(BaseModel):
    """A person as an identity provider reported them at login."""

    model_config = ConfigDict(frozen=True)

    issuer: str
    subject: str
    email: str | None = None
    email_verified: bool = False
    name: str | None = None


# Stored from a Python-mode dump, which would otherwise keep the enum member.
StoredRole = Annotated[Role, PlainSerializer(lambda role: role.value, return_type=str)]


class UserRecord(BaseModel):
    """A person who may do something, known by email until their first login binds their identity."""

    email: EmailStr = Field(description="The email address access was granted to.")
    issuer: str | None = Field(None, description="The identity provider of the person, bound at their first login.")
    subject: str | None = Field(None, description="The person's id at that identity provider, bound with it.")
    system_admin: bool = Field(False, description="Whether they may do anything, anywhere.")
    grants: dict[str, StoredRole] = Field({}, description="The role they have in each community, by slug.")

    @property
    def bound(self) -> bool:
        return self.subject is not None

    def has_email(self, email: str) -> bool:
        return str(self.email).casefold() == email.casefold()

    def matches(self, identity: Identity) -> bool:
        """Whether *identity* is this person.

        Once bound only the identity counts, so changing an email at the identity provider neither loses access nor
        hands it to whoever takes the old address. Before that, only a verified email does.
        """
        if self.bound:
            return (self.issuer, self.subject) == (identity.issuer, identity.subject)
        return identity.email_verified and identity.email is not None and self.has_email(identity.email)

    def bind(self, identity: Identity) -> None:
        self.issuer = identity.issuer
        self.subject = identity.subject


class Grant(BaseModel):
    """A role in one community, granted to the person with an email."""

    email: EmailStr = Field(description="The email address of the person the role is granted to.")
    role: Role = Field(description="The role granted.")
    bound: bool = Field(False, description="Whether that person has logged in since; reported, never written.")


class UsersFile(BaseModel):
    """Everyone who may do something, as stored."""

    # Read on every request, so an error in it must not quote what it holds back to whoever made one.
    model_config = ConfigDict(hide_input_in_errors=True)

    users: list[UserRecord] = []

    @model_validator(mode="after")
    def _check_emails_are_unique(self):
        emails = [str(user.email).casefold() for user in self.users]
        duplicates = sorted({email for email in emails if emails.count(email) > 1})
        if duplicates:
            raise ValueError(
                f"Each person can only be listed once, but {', '.join(duplicates)} is listed several times"
            )
        return self
