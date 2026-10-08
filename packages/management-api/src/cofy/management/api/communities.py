"""CRUD over communities - the configurations this management API manages.

The wire models here deliberately expose less than a stored config holds:

- `modules` belongs to `ModulesRouter`. Editing a title should not require sending, or be
  able to disturb, every module in the community.
- `auth` is omitted entirely. `TokenAuthSettings.tokens` is keyed *by the token*, so
  returning it would publish every machine-to-machine credential, and a `Secret` cannot mask
  a mapping key. Token management needs its own design.
- `debug_dir` is a local operational detail, and accepting a filesystem path from a client is
  a capability this API has no reason to hand out.

The listing answers "which communities may I see", so a client never has to work that out for
itself; what it may do in each is reported by `/auth/me`.
"""

from __future__ import annotations

from typing import Annotated

from cofy.api.cofy_api import CofyAPISettings
from fastapi import Body, Depends, Path
from pydantic import BaseModel, Field

from ..auth.access import Subject
from ..auth.user import User, current_user
from ..community_api import CommunityApi
from ..persitance.communities import CommunitiesPersistence
from ..persitance.grants import GrantsPersistence
from ..policies.community import CommunityPolicy
from ..policies.policy import PolicyRouter

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
    revision: int | None = Field(description="The revision of the settings, raised on every change.")
    api_url: str = Field(description="Where the community's own API is served.")

    @classmethod
    def of(cls, slug: str, settings: CofyAPISettings, api_url: str) -> CommunityInfo:
        return cls(
            slug=slug,
            title=settings.title,
            description=settings.description,
            debug_mode=settings.debug_mode,
            module_count=len(settings.modules),
            revision=settings.revision,
            api_url=api_url,
        )


class CommunitiesRouter:
    def __init__(self, persitance: CommunitiesPersistence, grants: GrantsPersistence, api: CommunityApi):
        self.persistence = persitance
        self.grants = grants
        self.api = api
        self.router = PolicyRouter(
            subject=Subject.community, policy=CommunityPolicy, prefix="/management/communities", tags=["Communities"]
        )
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("", self.all, methods=["GET"], rule=CommunityPolicy.all)
        self.router.add_api_route("", self.create, methods=["POST"], rule=CommunityPolicy.create, status_code=201)
        self.router.add_api_route("/{slug}", self.get, methods=["GET"], rule=CommunityPolicy.get)
        self.router.add_api_route("/{slug}", self.put, methods=["PUT"], rule=CommunityPolicy.put)
        self.router.add_api_route(
            "/{slug}", self.delete, methods=["DELETE"], rule=CommunityPolicy.delete, status_code=204
        )

    def all(self, user: Annotated[User, Depends(current_user)]) -> list[CommunityInfo]:
        communities = dict(self.persistence.all())
        return [self._info(slug, communities[slug]) for slug in CommunityPolicy.scope(user, list(communities))]

    def get(
        self,
        slug: Annotated[str, Path(description="Community slug")],
    ) -> CommunityInfo:
        return self._info(slug, self.persistence.get(slug))

    def create(
        self,
        payload: Annotated[CommunityCreate, Body(description="Community settings")],
    ) -> CommunityInfo:
        return self._info(payload.slug, self.persistence.create(payload.slug, payload.to_settings()))

    def put(
        self,
        slug: str,
        payload: Annotated[CommunityBody, Body(description="Community settings")],
    ) -> CommunityInfo:
        return self._info(slug, self.persistence.update(slug, payload.to_settings()))

    def _info(self, slug: str, settings: CofyAPISettings) -> CommunityInfo:
        return CommunityInfo.of(slug, settings, self.api.url(slug))

    def delete(self, slug: str) -> None:
        # Revoked first, or a community created later under the same slug could inherit them; should deleting then
        # fail, the community is left without anyone having access, rather than access without a community. Its
        # config isn't read, so a community whose config is broken can still be deleted.
        self.grants.delete_all(slug)
        self.persistence.delete(slug)
        return None
