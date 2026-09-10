import fcntl
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from cofy.api.cofy_api import CofyAPISettings

from ...errors import ResourceNotFoundError

PACKAGED_BASE_PATH = Path(str(resources.files("cofy.management.persitance.file") / "data"))
"""Sample communities shipped with the package, used when no data directory is configured."""

DATA_DIR_ENV_VAR = "COFY_MANAGEMENT_DATA_DIR"

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
"""Characters a community slug may contain, matching the rule for module names."""


def default_base_path() -> Path:
    """Where community configs live.

    The packaged samples are fine to read but not to write - that path is inside the
    installed distribution - so a deployment that edits communities must set the
    environment variable.
    """
    configured = os.environ.get(DATA_DIR_ENV_VAR)
    return Path(configured) if configured else PACKAGED_BASE_PATH


class FilePersistence:
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

    @contextmanager
    def _open_community_config(self, slug: str, mode: Literal["read", "write"]) -> Generator[CofyAPISettings]:
        """Open a community's config for either a read or a read-modify-write.

        `mode="read"` takes a *shared* lock: it excludes a concurrent write (so a reader is
        never handed a config mid-write - the write path truncates the file before rewriting
        it, and an unlocked read landing in that window would see a torn, unparseable file),
        but it does not exclude other concurrent reads. Nothing is written back.

        `mode="write"` takes an *exclusive* lock, excluding readers and writers alike for the
        duration of the block, so concurrent requests against the same community serialize
        instead of racing each other's read-modify-write. If the block completes normally,
        the (possibly mutated) config is written back automatically; if it raises - e.g. a
        not-found or already-exists error - nothing is written.

        Either way, the lock is always released. It is a plain `flock` on the config file
        itself, so it holds across both threads and processes without needing a separate
        lock file - but it is advisory and POSIX-only: it only excludes other code that goes
        through this same method, and it is not available on Windows.
        """
        path = self._community_path(slug)
        if not path.exists():
            raise ResourceNotFoundError(f"Community {slug!r} not found")

        file_mode = "r+" if mode == "write" else "r"
        lock_flag = fcntl.LOCK_EX if mode == "write" else fcntl.LOCK_SH

        with path.open(file_mode, encoding="utf-8") as handle:
            fcntl.flock(handle, lock_flag)
            try:
                loaded = yaml.safe_load(handle) or {}
                if not isinstance(loaded, dict):
                    raise ValueError(f"Community config at {path} must be a YAML mapping")

                config = CofyAPISettings.model_validate(loaded)
                yield config

                if mode == "write":
                    # Serialize before truncating, so a dump that raises leaves the previous
                    # contents alone instead of emptying the file.
                    dumped = yaml.safe_dump(
                        config.model_dump(exclude_none=True, polymorphic_serialization=True, round_trip=True),
                        sort_keys=True,
                    )
                    handle.seek(0)
                    handle.truncate()
                    handle.write(dumped)
                    # Flush inside the lock: the write is buffered and the lock is released
                    # before the handle is closed, so without this the next reader could take
                    # the lock and still see the truncated file.
                    handle.flush()
                    os.fsync(handle.fileno())
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
