"""CRUD over a community's API tokens, whose keys are generated here, shown once and stored only as a hash."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from cofy.api import TokenInfo, generate_key, hash_key
from cofy.api.secret import NAME_PATTERN
from fastapi import Path
from pydantic import BaseModel, Field

from ..auth.access import Subject
from ..persitance.tokens import TokensPersistence
from ..policies.policy import Policy, PolicyRouter


class TokenBody(BaseModel):
    """An API token as written: everything but its key, which is only ever generated."""

    name: str = Field(description="The machine name of the token.", pattern=NAME_PATTERN)
    description: str | None = Field(None, description="A short description of the token, e.g. who uses it.")
    expires: datetime | None = Field(None, description="When the token stops being accepted.")

    def to_settings(self, hash: str) -> TokenInfo:
        return TokenInfo(name=self.name, description=self.description, expires=self.expires, hash=hash)


class TokenDetails(BaseModel):
    """An API token as reported: everything but its key and hash."""

    name: str
    description: str | None = None
    expires: datetime | None = None

    @classmethod
    def of(cls, token: TokenInfo) -> TokenDetails:
        return cls(name=token.name, description=token.description, expires=token.expires)


class CreatedToken(TokenDetails):
    """A newly created API token, with its key: the only time it is ever reported."""

    key: str = Field(description="The key itself, to keep now: it can't be shown again.")


class TokensRouter:
    def __init__(self, persistence: TokensPersistence):
        self.persistence = persistence
        self.router = PolicyRouter(
            subject=Subject.tokens, prefix="/management/communities/{slug}/tokens", tags=["Tokens"]
        )
        self.router.add_api_route("", self.all, methods=["GET"], rule=Policy.all)
        self.router.add_api_route("/{name}", self.get, methods=["GET"], rule=Policy.get)
        self.router.add_api_route("", self.create, methods=["POST"], rule=Policy.create, status_code=201)
        self.router.add_api_route("/{name}", self.put, methods=["PUT"], rule=Policy.put)
        self.router.add_api_route("/{name}", self.delete, methods=["DELETE"], rule=Policy.delete, status_code=204)

    def all(self, slug: Annotated[str, Path(description="Community slug")]) -> list[TokenDetails]:
        return [TokenDetails.of(token) for token in self.persistence.all(slug)]

    def get(self, slug: str, name: str) -> TokenDetails:
        return TokenDetails.of(self.persistence.get(slug, name))

    def create(self, slug: str, payload: TokenBody) -> CreatedToken:
        key = generate_key()
        token = self.persistence.create(slug, payload.to_settings(hash_key(key)))
        return CreatedToken(**TokenDetails.of(token).model_dump(), key=key)

    def put(self, slug: str, name: str, payload: TokenBody) -> TokenDetails:
        if payload.name != name:
            raise ValueError(f"Token name in body ({payload.name!r}) must match the URL path ({name!r})")
        # Kept as a hash, so a key written into the config by hand isn't stored in plain text by this API either.
        digest = self.persistence.get(slug, name).digest()
        return TokenDetails.of(self.persistence.replace(slug, name, payload.to_settings(digest)))

    def delete(self, slug: str, name: str) -> None:
        self.persistence.delete(slug, name)
        return None
