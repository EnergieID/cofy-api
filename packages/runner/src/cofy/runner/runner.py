"""Serves a directory of community settings, each as the Cofy API it describes, rebuilt whenever its settings change."""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import yaml
from cofy.api import CofyAPI
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

logger = logging.getLogger(__name__)

Signature = tuple[int, int, int]
"""What tells one version of a settings file from the next: its inode, modification time and size."""


@dataclass(frozen=True)
class Community:
    """A community as the runner has it."""

    app: CofyAPI | None
    """The API it serves, or `None` when its settings have never built."""
    signature: Signature
    """The version of the settings file last built, or tried to."""


class CommunityRunner(Starlette):
    """Every community in *directory*, each `<slug>.yaml` served under `/<slug>/`.

    The directory is checked every *poll_interval*, and a community whose file changed is rebuilt and swapped in; one
    that fails to build keeps serving what it served before. *communities* limits which slugs are served, so several
    runners can share one directory.
    """

    def __init__(
        self,
        directory: Path,
        communities: frozenset[str] | None = None,
        poll_interval: dt.timedelta = dt.timedelta(seconds=2),
    ):
        self.directory = directory
        self.communities = communities
        self.poll_interval = poll_interval
        self._served: dict[str, Community] = {}
        super().__init__(
            routes=[Mount("/{slug}", app=self.dispatch)],
            lifespan=self._lifespan,
        )

    def community(self, slug: str) -> Community | None:
        return self._served.get(slug)

    async def refresh(self) -> None:
        """Build every community whose settings changed since they were last built, and drop those that are gone."""
        found = {
            path.stem: path
            for path in sorted(self.directory.glob("*.yaml"))
            if self.communities is None or path.stem in self.communities
        }

        for slug in self._served.keys() - found.keys():
            del self._served[slug]
            logger.info("Community %r is no longer served", slug, extra={"community": slug})

        for slug, path in found.items():
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue  # deleted since it was listed; the next refresh drops it
            signature = (stat.st_ino, stat.st_mtime_ns, stat.st_size)
            previous = self._served.get(slug)
            if previous is None or previous.signature != signature:
                # In a thread, as building one may read files or wait on the network, which mustn't hold up requests.
                self._served[slug] = await asyncio.to_thread(self._build, slug, path, signature, previous)

    @staticmethod
    def _build(slug: str, path: Path, signature: Signature, previous: Community | None) -> Community:
        try:
            settings = yaml.safe_load(path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                raise ValueError(f"{path.name} must be a YAML mapping")
            app = CofyAPI.create(settings)
        except Exception:
            logger.exception("Community %r failed to build from %s", slug, path.name, extra={"community": slug})
            return Community(app=previous.app if previous else None, signature=signature)

        logger.info("Community %r runs revision %s", slug, app.revision, extra={"community": slug})
        return Community(app=app, signature=signature)

    async def dispatch(self, scope: Scope, receive: Receive, send: Send) -> None:
        community = self._served.get(scope["path_params"]["slug"])
        if community is None:
            response = JSONResponse({"detail": "Not Found"}, status_code=404)
        elif community.app is None:
            response = JSONResponse({"detail": "Service Unavailable"}, status_code=503)
        else:
            await community.app(scope, receive, send)
            return
        await response(scope, receive, send)

    @asynccontextmanager
    async def _lifespan(self, app: Starlette) -> AsyncGenerator[None]:
        await self.refresh()
        polling = asyncio.create_task(self._poll())
        try:
            yield
        finally:
            polling.cancel()
            with suppress(asyncio.CancelledError):
                await polling

    async def _poll(self) -> None:
        while True:
            await asyncio.sleep(self.poll_interval.total_seconds())
            try:
                await self.refresh()
            except Exception:
                logger.exception("Checking %s for changed settings failed", self.directory)
