import logging
import os

import yaml
from cofy.api.cofy_api import CofyAPISettings

from ...errors import ManagementError, ResourceAlreadyExistsError
from ..communities import CommunitiesPersistence
from .base import FilePersistence

#: Community-level fields a client may set. Everything else in a stored config either belongs
#: to another endpoint (`modules`), is managed outside the console (`auth`, whose token map
#: cannot be masked because the tokens are dict *keys*), or is a local operational detail
#: (`debug_dir`).
WRITABLE_FIELDS = ("title", "description", "debug_mode")

logger = logging.getLogger(__name__)


class FileCommunitiesPersistence(FilePersistence, CommunitiesPersistence):
    def all(self) -> list[tuple[str, CofyAPISettings]]:
        communities = []
        for slug in self._community_slugs():
            try:
                with self._open_community_config(slug, "read") as config:
                    communities.append((slug, config))
            except (ValueError, yaml.YAMLError, ManagementError) as exc:
                # These configs are hand-editable by design, so one bad edit is expected
                # eventually - and this listing is the console's entry point. Dropping the
                # unreadable community keeps the rest reachable, where failing the whole
                # request would leave an operator with no way in to fix anything. Reading
                # that community directly still reports the parse error in full.
                logger.warning("Skipping unreadable community %r: %s", slug, exc)
        return communities

    def get(self, slug: str) -> CofyAPISettings:
        with self._open_community_config(slug, "read") as config:
            return config

    def create(self, slug: str, settings: CofyAPISettings) -> CofyAPISettings:
        path = self._community_path(slug)  # also validates the slug before it becomes a filename
        self.base_path.mkdir(parents=True, exist_ok=True)

        dumped = yaml.safe_dump(
            settings.model_dump(exclude_none=True, polymorphic_serialization=True, round_trip=True),
            sort_keys=True,
        )
        try:
            # O_EXCL makes the existence check and the create one atomic step, so two
            # concurrent creates of the same slug cannot both believe they won.
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError as exc:
            raise ResourceAlreadyExistsError(f"Community {slug!r} already exists") from exc

        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumped)
            handle.flush()
            os.fsync(handle.fileno())

        return settings

    def update(self, slug: str, settings: CofyAPISettings) -> CofyAPISettings:
        with self._open_community_config(slug, "write") as config:
            # Assign only the community's own fields. `modules` and `auth` are deliberately
            # not touched, and the write-back re-serializes the whole stored config, so they
            # round-trip untouched rather than needing to be copied across.
            for field in WRITABLE_FIELDS:
                setattr(config, field, getattr(settings, field))
            return config

    def delete(self, slug: str) -> None:
        # Opening for read proves the community exists and takes a lock that excludes a
        # concurrent write; the file is removed once that lock has been released.
        with self._open_community_config(slug, "read"):
            pass
        self._community_path(slug).unlink()
