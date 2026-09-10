"""CRUD over communities - the configurations this management API manages.

The wire models here deliberately expose less than a stored config holds:

- `modules` belongs to `ModulesRouter`. Editing a title should not require sending, or be
  able to disturb, every module in the community.
- `auth` is omitted entirely. `TokenAuthSettings.tokens` is keyed *by the token*, so
  returning it would publish every machine-to-machine credential, and a `Secret` cannot mask
  a mapping key. Token management needs its own design.
- `debug_dir` is a local operational detail, and accepting a filesystem path from a client is
  a capability this API has no reason to hand out.

This listing is also where authorization will land: it answers "which communities may I
see", so a client must never assemble that list for itself.
"""

from __future__ import annotations

from typing import Annotated

from cofy.api.cofy_api import CofyAPISettings
from fastapi import APIRouter, Body, Path
from pydantic import BaseModel, Field

from ..persitance.communities import CommunitiesPersistence

SLUG_FIELD = Field(
    description="Machine name, and the community's identity in every other route.",
    pattern=r"^[a-zA-Z0-9_-]+$",
)


class CommunityBody(BaseModel):
    """The community-level settings a client may set."""

    title: str = Field(description="Human-readable name of the community.")
    description: str = Field("", description="What this community is for.")
    debug_mode: bool = Field(False, description="Whether the runtime records debug traces.")

    def to_settings(self) -> CofyAPISettings:
        """Carry the writable fields into a settings object.

        On an update the persistence layer copies just those fields onto the stored config,
        so the empty `modules` and absent `auth` here are never written anywhere.
        """
        return CofyAPISettings(
            title=self.title,
            description=self.description,
            debug_mode=self.debug_mode,
        )


class CommunityCreate(CommunityBody):
    slug: str = SLUG_FIELD


class CommunityInfo(CommunityBody):
    """A community as reported by this API - its own settings, not its contents."""

    slug: str = SLUG_FIELD
    module_count: int = Field(description="How many modules are configured, for listings.")

    @classmethod
    def of(cls, slug: str, settings: CofyAPISettings) -> CommunityInfo:
        return cls(
            slug=slug,
            title=settings.title,
            description=settings.description,
            debug_mode=settings.debug_mode,
            module_count=len(settings.modules),
        )


class CommunitiesRouter:
    def __init__(self, persitance: CommunitiesPersistence):
        self.persistence = persitance
        self.router = APIRouter(prefix="/management/communities", tags=["Communities"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("", self.all, methods=["GET"])
        self.router.add_api_route("", self.create, methods=["POST"], status_code=201)
        self.router.add_api_route("/{slug}", self.get, methods=["GET"])
        self.router.add_api_route("/{slug}", self.put, methods=["PUT"])
        self.router.add_api_route("/{slug}", self.delete, methods=["DELETE"], status_code=204)

    def all(self) -> list[CommunityInfo]:
        return [CommunityInfo.of(slug, settings) for slug, settings in self.persistence.all()]

    def get(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> CommunityInfo:
        return CommunityInfo.of(slug, self.persistence.get(slug))

    def create(
        self,
        payload: Annotated[CommunityCreate, Body(description="Community settings")],
    ) -> CommunityInfo:
        return CommunityInfo.of(payload.slug, self.persistence.create(payload.slug, payload.to_settings()))

    def put(
        self,
        slug: str,
        payload: Annotated[CommunityBody, Body(description="Community settings")],
    ) -> CommunityInfo:
        return CommunityInfo.of(slug, self.persistence.update(slug, payload.to_settings()))

    def delete(self, slug: str) -> None:
        self.persistence.delete(slug)
        return None
