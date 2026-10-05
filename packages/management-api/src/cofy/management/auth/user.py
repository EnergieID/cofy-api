from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, Request

from ..persitance.users import UsersPersistence
from .access import ROLE_PERMISSIONS, Action, Identity, Permission, Role, Subject, UserRecord
from .session import current_identity


class User:
    """The person making a request, and what they may do."""

    def __init__(self, identity: Identity, record: UserRecord | None):
        self.identity = identity
        self.record = record

    @property
    def system_admin(self) -> bool:
        return self.record is not None and self.record.system_admin

    def role_in(self, slug: str) -> Role | None:
        return self.record.grants.get(slug) if self.record is not None else None

    def permissions(self, slug: str | None) -> frozenset[Permission]:
        """What the user may do in community *slug*, or outside any one community when it is `None` - which, but for
        a system admin, is nothing."""
        if self.system_admin:
            return frozenset(Permission.all())
        if slug is None:
            return frozenset()
        role = self.role_in(slug)
        return ROLE_PERMISSIONS[role] if role is not None else frozenset()

    def communities(self) -> list[str]:
        """The communities the user has a role in."""
        return list(self.record.grants) if self.record is not None else []

    def can(self, action: Action, subject: Subject, slug: str | None) -> bool:
        return Permission(action=action, subject=subject) in self.permissions(slug)


def install_users(app: FastAPI, users: UsersPersistence) -> None:
    """Have *app* look up who may do what in *users*."""
    app.state.users = users


def current_user(request: Request, identity: Annotated[Identity, Depends(current_identity)]) -> User:
    """The person making this request."""
    users: UsersPersistence = request.app.state.users
    return User(identity, users.match(identity))
