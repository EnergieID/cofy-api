"""Logged-in users for tests, standing in for a login through the identity provider."""

from __future__ import annotations

from fastapi import FastAPI

from cofy.management.auth.access import Identity, Role, UserRecord
from cofy.management.auth.config import OidcConfig
from cofy.management.auth.user import User, current_user

ISSUER = "https://identity.example"

OIDC_CONFIG = OidcConfig(
    issuer=ISSUER,
    client_id="cofy-management",
    client_secret="client-secret",
    session_secret="session-secret",
    secure_cookies=False,
)


def identity(name: str) -> Identity:
    return Identity(issuer=ISSUER, subject=f"{name}-sub", email=f"{name}@example.com", email_verified=True, name=name)


def log_in(app: FastAPI, user: User) -> None:
    """Have every request to *app* made by *user*."""
    app.dependency_overrides[current_user] = lambda: user


def user(name: str, *, system_admin: bool = False, grants: dict[str, Role] | None = None) -> User:
    """*name* logged in, as the users file would have them."""
    record = UserRecord(email=f"{name}@example.com", issuer=ISSUER, subject=f"{name}-sub", system_admin=system_admin)
    record.grants = grants or {}
    return User(identity(name), record)


def log_in_as_system_admin(app: FastAPI) -> None:
    log_in(app, user("admin", system_admin=True))
