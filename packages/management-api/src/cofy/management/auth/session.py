"""The login session: a signed cookie holding who logged in, until when.

The cookie is `SameSite=Lax`, so a browser only sends it cross-site on top-level `GET` navigations, which change
nothing here; that, and the API taking JSON bodies, is what keeps other sites from making requests on a user's behalf.
"""

from __future__ import annotations

import datetime as dt

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware

from ..errors import NotAuthenticatedError
from .access import Identity
from .config import OidcConfig

COOKIE_NAME = "cofy_session"


def install_session(app: FastAPI, config: OidcConfig) -> None:
    """Have *app* keep login sessions in a signed cookie."""
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.session_secret.get_secret_value(),
        session_cookie=COOKIE_NAME,
        max_age=int(config.session_lifetime.total_seconds()),
        same_site="lax",
        https_only=config.secure_cookies,
    )


def start_session(request: Request, identity: Identity, id_token: str | None, lifetime: dt.timedelta) -> None:
    """Log *identity* in on this browser, replacing whatever session it had."""
    request.session.clear()
    request.session.update(
        {
            "identity": identity.model_dump(mode="json"),
            "id_token": id_token,
            # Expiry is absolute: the cookie's own max-age is renewed on every response, so it alone would let a
            # session that's in use last forever.
            "expires_at": (dt.datetime.now(dt.UTC) + lifetime).timestamp(),
        }
    )


def current_identity(request: Request) -> Identity:
    """Who is logged in on this request."""
    session = request.session
    expires_at = session.get("expires_at")
    if "identity" not in session or expires_at is None or expires_at <= dt.datetime.now(dt.UTC).timestamp():
        raise NotAuthenticatedError("Not logged in")
    return Identity.model_validate(session["identity"])
