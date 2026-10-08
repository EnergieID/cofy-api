"""The communities' own APIs, as far as this API needs to know them: where each is served, and what it runs."""

from __future__ import annotations

import logging
from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class ApiHealth(BaseModel):
    """What a community's API reports about itself."""

    status: Literal["ok", "unknown", "unavailable"]
    """`ok` when it runs, `unknown` when nothing serves it (yet), and `unavailable` when it doesn't run."""
    revision: int | None = None
    """The revision of the settings it runs."""


class CommunityApi:
    """The API of each community, served under its slug at the base URL of *client*."""

    def __init__(self, client: httpx.Client):
        self.client = client

    def url(self, slug: str) -> str:
        return f"{str(self.client.base_url).rstrip('/')}/{slug}/"

    def health(self, slug: str) -> ApiHealth:
        try:
            response = self.client.get(f"{slug}/health")
        except httpx.HTTPError as exc:
            logger.warning("The API of community %r can't be reached: %s", slug, exc)
            return ApiHealth(status="unavailable")

        if response.status_code == 404:
            return ApiHealth(status="unknown")
        try:
            response.raise_for_status()
            return ApiHealth.model_validate_json(response.content)
        except (httpx.HTTPStatusError, ValidationError):
            logger.warning("The API of community %r answered %s to a health check", slug, response.status_code)
            return ApiHealth(status="unavailable")
