"""Logging in and out through an OpenID Connect provider, which this API is the client of.

The browser never sees a token: the provider hands the login back to this API, which keeps only who logged in, in the
session cookie.
"""

from __future__ import annotations

import logging
from typing import Annotated
from urllib.parse import urlencode

import httpx
from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from ..persitance.communities import CommunitiesPersistence
from ..persitance.users import UsersPersistence
from ..policies.policy import PUBLIC, Policy, PolicyRouter
from .access import Identity, Permission
from .config import OidcConfig
from .session import start_session
from .user import User, current_user

logger = logging.getLogger(__name__)


class CommunityPermissions(BaseModel):
    """What the person logged in may do in one community, or outside any one community."""

    slug: str | None = Field(description="The community, or `null` for what lies outside any one community.")
    permissions: list[Permission]


class Me(BaseModel):
    """The person logged in."""

    email: str | None
    name: str | None
    system_admin: bool
    permissions: list[CommunityPermissions] = Field(
        description="What they may do, outside any one community and in each community they may do anything in."
    )


def safe_return_to(return_to: str | None) -> str:
    """*return_to* if it is a path on this site, so a login link can't send anyone elsewhere; the root otherwise."""
    if return_to and return_to.startswith("/") and not return_to.startswith("//") and "\\" not in return_to:
        return return_to
    return "/"


class AuthRouter:
    def __init__(self, config: OidcConfig, users: UsersPersistence, communities: CommunitiesPersistence):
        self.config = config
        self.users = users
        self.communities = communities
        self.oauth = OAuth()
        self.oauth.register(
            "oidc",
            client_id=config.client_id,
            client_secret=config.client_secret.get_secret_value(),
            server_metadata_url=config.server_metadata_url,
            client_kwargs={"scope": config.scopes, "code_challenge_method": "S256"},
        )
        self.router = PolicyRouter(subject=None, prefix="/auth", tags=["Authentication"])
        self.router.add_api_route("/login", self.login, methods=["GET"], rule=PUBLIC)
        self.router.add_api_route("/callback", self.callback, methods=["GET"], rule=PUBLIC, name="auth_callback")
        self.router.add_api_route("/logout", self.logout, methods=["POST"], rule=PUBLIC)
        self.router.add_api_route("/me", self.me, methods=["GET"], rule=Policy.authenticated)

    @property
    def client(self):
        return self.oauth.create_client("oidc")

    async def login(self, request: Request, return_to: Annotated[str | None, Query()] = None) -> RedirectResponse:
        """Send the browser to the identity provider, to come back to *return_to* once logged in."""
        request.session["return_to"] = safe_return_to(return_to)
        return await self.client.authorize_redirect(request, str(request.url_for("auth_callback")))

    async def callback(self, request: Request) -> RedirectResponse:
        """Where the identity provider sends the browser back to after a login."""
        token = await self.client.authorize_access_token(request)
        claims = await self._claims(token)
        identity = Identity(
            issuer=claims["iss"],
            subject=claims["sub"],
            email=claims.get("email"),
            email_verified=claims.get("email_verified") in (True, "true"),
            name=claims.get("name"),
        )
        self.users.bind(identity)
        return_to = safe_return_to(request.session.get("return_to"))
        start_session(request, identity, token.get("id_token"), self.config.session_lifetime)
        return RedirectResponse(return_to, status_code=303)

    async def _claims(self, token: dict) -> dict:
        """The ID token's claims, completed from the userinfo endpoint when the email isn't among them.

        Providers such as Duende IdentityServer leave profile claims out of the ID token by default.
        """
        claims = dict(token["userinfo"])
        if "email" not in claims and (await self.client.load_server_metadata()).get("userinfo_endpoint"):
            userinfo = await self.client.userinfo(token=token)
            # The userinfo response must be about the same person, or none of it is used.
            if userinfo.get("sub") == claims["sub"]:
                claims = {**userinfo, **claims}
        return claims

    async def logout(self, request: Request) -> RedirectResponse:
        """End the session here, and at the identity provider if it lets clients do that."""
        id_token = request.session.get("id_token")
        request.session.clear()
        try:
            metadata = await self.client.load_server_metadata()
        except httpx.HTTPError as exc:
            # The session here is already over; an identity provider that can't be reached only means its own
            # session outlives it.
            logger.warning("Could not reach the identity provider to log out there too: %s", exc)
            return RedirectResponse("/", status_code=303)
        end_session = metadata.get("end_session_endpoint")
        if not end_session:
            return RedirectResponse("/", status_code=303)
        params = {"post_logout_redirect_uri": str(request.base_url), "client_id": self.config.client_id}
        if id_token:
            params["id_token_hint"] = id_token
        return RedirectResponse(f"{end_session}?{urlencode(params)}", status_code=303)

    def me(self, user: Annotated[User, Depends(current_user)]) -> Me:
        slugs: list[str | None] = [None, *(slug for slug, _ in self.communities.all())]
        permissions = [(slug, user.permissions(slug)) for slug in slugs]
        return Me(
            email=user.identity.email,
            name=user.identity.name,
            system_admin=user.system_admin,
            permissions=[
                CommunityPermissions(
                    slug=slug,
                    # In a stable order, for a client and a test alike.
                    permissions=[permission for permission in Permission.all() if permission in granted],
                )
                for slug, granted in permissions
                if granted
            ],
        )
