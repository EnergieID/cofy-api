"""Whether a community's API runs its saved settings, in the few states a community admin can make sense of.

What went wrong, when something did, is for whoever hosts the communities' APIs, who finds it in their log; the states
only tell a community admin whether their changes are in effect.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, Field

from ..auth.access import Subject
from ..community_api import ApiHealth, CommunityApi
from ..persitance.communities import CommunitiesPersistence
from ..policies.policy import Policy, PolicyRouter


class CommunityState(StrEnum):
    live = "live"
    pending = "pending"
    unavailable = "unavailable"


class CommunityStatus(BaseModel):
    state: CommunityState = Field(
        description="`live` when the API runs the saved settings, `pending` while it runs earlier ones - for a few "
        "seconds after a change, or for as long as the change fails to apply - and `unavailable` when it doesn't run."
    )
    revision: int | None = Field(description="The revision of the saved settings.")
    running_revision: int | None = Field(description="The revision of the settings the API runs, if it runs.")

    @classmethod
    def of(cls, revision: int | None, health: ApiHealth) -> CommunityStatus:
        return cls(state=cls._state(revision, health), revision=revision, running_revision=health.revision)

    @staticmethod
    def _state(revision: int | None, health: ApiHealth) -> CommunityState:
        match health.status:
            case "ok":
                return CommunityState.live if health.revision == revision else CommunityState.pending
            case "unknown":
                return CommunityState.pending
            case "unavailable":
                return CommunityState.unavailable


class StatusRouter:
    def __init__(self, persistence: CommunitiesPersistence, api: CommunityApi):
        self.persistence = persistence
        self.api = api
        self.router = PolicyRouter(
            subject=Subject.community, prefix="/management/communities/{slug}/status", tags=["Communities"]
        )
        self.router.add_api_route("", self.get, methods=["GET"], rule=Policy.get)

    def get(self, slug: Annotated[str, Path(description="Community slug")]) -> CommunityStatus:
        # Read first, so a community that doesn't exist is a 404 rather than a question to its API.
        revision = self.persistence.get(slug).revision
        return CommunityStatus.of(revision, self.api.health(slug))
