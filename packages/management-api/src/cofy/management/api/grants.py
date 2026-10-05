"""Who has access to a community: roles granted by email, bound to the person's identity at their first login.

They are kept with the people they are granted to, rather than in the community's config.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, EmailStr, Field

from ..auth.access import Grant, Role, Subject
from ..persitance.communities import CommunitiesPersistence
from ..persitance.grants import GrantsPersistence
from ..policies.policy import Policy, PolicyRouter


class GrantBody(BaseModel):
    """A grant as written; who it is bound to is only ever set by that person logging in."""

    email: EmailStr = Field(description="The email address of the person the role is granted to.")
    role: Role = Field(description="The role granted.")


class GrantInfo(BaseModel):
    """A grant as reported."""

    email: str
    role: Role
    bound: bool = Field(description="Whether the person has logged in since, tying the grant to their account.")

    @classmethod
    def of(cls, grant: Grant) -> GrantInfo:
        return cls(email=str(grant.email), role=grant.role, bound=grant.bound)


class GrantsRouter:
    def __init__(self, persistence: GrantsPersistence, communities: CommunitiesPersistence):
        self.persistence = persistence
        self.communities = communities
        self.router = PolicyRouter(
            subject=Subject.grants, prefix="/management/communities/{slug}/grants", tags=["Grants"]
        )
        self.router.add_api_route("", self.all, methods=["GET"], rule=Policy.all)
        self.router.add_api_route("/{email}", self.get, methods=["GET"], rule=Policy.get)
        self.router.add_api_route("", self.create, methods=["POST"], rule=Policy.create, status_code=201)
        self.router.add_api_route("/{email}", self.put, methods=["PUT"], rule=Policy.put)
        self.router.add_api_route("/{email}", self.delete, methods=["DELETE"], rule=Policy.delete, status_code=204)

    def all(self, slug: Annotated[str, Path(description="Community slug")]) -> list[GrantInfo]:
        self.communities.get(slug)
        return [GrantInfo.of(grant) for grant in self.persistence.all(slug)]

    def get(self, slug: str, email: str) -> GrantInfo:
        self.communities.get(slug)
        return GrantInfo.of(self.persistence.get(slug, email))

    def create(self, slug: str, payload: GrantBody) -> GrantInfo:
        self.communities.get(slug)
        return GrantInfo.of(self.persistence.create(slug, Grant(email=payload.email, role=payload.role)))

    def put(self, slug: str, email: str, payload: GrantBody) -> GrantInfo:
        """Change the role granted; a different person is a grant of its own."""
        if str(payload.email).casefold() != email.casefold():
            raise ValueError(f"Email in body ({str(payload.email)!r}) must match the URL path ({email!r})")
        self.communities.get(slug)
        return GrantInfo.of(self.persistence.replace(slug, email, Grant(email=payload.email, role=payload.role)))

    def delete(self, slug: str, email: str) -> None:
        self.communities.get(slug)
        self.persistence.delete(slug, email)
        return None
