import re
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import yaml
from cofy.api.cofy_api import CofyAPISettings

from ....errors import ManagementError, ResourceNotFoundError
from .store import FileStore, data_dir

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
"""Characters a community slug may contain, matching the rule for module names."""


def default_base_path() -> Path:
    """Where community configs live."""
    return data_dir() / "communities"


class CommunityFileStore(FileStore[CofyAPISettings]):
    """Community configs, one YAML file per community, named after its slug."""

    document = CofyAPISettings

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path if base_path is not None else default_base_path()

    def _community_path(self, slug: str) -> Path:
        # A slug becomes a filename, so anything outside the pattern - a separator, a `..`, a
        # leading dot - could address a file outside the data directory. The HTTP layer
        # happens to reject most of that, but a slug also arrives in a request body when a
        # community is created, where nothing else is checking.
        if not SLUG_PATTERN.match(slug):
            raise ValueError(f"Community slug {slug!r} must match {SLUG_PATTERN.pattern}")
        return self.base_path / f"{slug}.yaml"

    def _community_slugs(self) -> list[str]:
        """Every community that exists, in a stable order."""
        if not self.base_path.is_dir():
            return []
        return sorted(path.stem for path in self.base_path.glob("*.yaml"))

    def _not_found(self, path: Path) -> ManagementError:
        return ResourceNotFoundError(f"Community {path.stem!r} not found")

    def _serialize(self, document: CofyAPISettings) -> str:
        """As in `FileStore._serialize`, for a community config: a fresh `create` and a
        read-modify-write alike.

        The config is validated again as a whole, exactly as it will be read back: a write
        that edits one part can break a rule spanning several, like a module referencing a
        resource, and must fail rather than store a config that can't be read anymore."""
        dumped = document.model_dump(exclude_none=True, polymorphic_serialization=True, round_trip=True)
        CofyAPISettings.model_validate(dumped)
        return yaml.safe_dump(dumped, sort_keys=True)

    @contextmanager
    def _open_community_config(self, slug: str, mode: Literal["read", "write"]) -> Generator[CofyAPISettings]:
        """Open a community's config for either a read or a read-modify-write, see `_open_document`."""
        with self._open_document(self._community_path(slug), mode) as config:
            yield config
