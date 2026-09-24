import fcntl
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Literal

import yaml
from cofy.api.cofy_api import CofyAPISettings

from ...errors import ResourceNotFoundError

DATA_DIR_ENV_VAR = "COFY_MANAGEMENT_DATA_DIR"

SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
"""Characters a community slug may contain, matching the rule for module names."""


def default_base_path() -> Path:
    """Where community configs live.

    There is no built-in default: this is a deployment's writable state, not something the
    library can guess at or ship a sample of, so the environment variable is required.
    """
    configured = os.environ.get(DATA_DIR_ENV_VAR)
    if not configured:
        raise RuntimeError(f"{DATA_DIR_ENV_VAR} must be set to a writable directory for community configs")
    return Path(configured)


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

    @staticmethod
    def _serialize(config: CofyAPISettings) -> str:
        """The on-disk YAML form of *config* - the one place a validated config is turned back
        into text, so every write path (a fresh `create`, or a read-modify-write) stays
        byte-for-byte consistent instead of quietly drifting apart."""
        return yaml.safe_dump(
            config.model_dump(exclude_none=True, polymorphic_serialization=True, round_trip=True),
            sort_keys=True,
        )

    @contextmanager
    def _locked_file(self, slug: str, *, exclusive: bool, writable: bool = False) -> Generator[IO[str]]:
        """Open *slug*'s config file and hold a lock on it for the duration of the block.

        A *shared* lock (`exclusive=False`) excludes a concurrent exclusive lock (a write or a
        delete) - so a reader is never handed a config mid-write, or one that has just been
        deleted - without excluding other concurrent shared holders (other reads). An
        *exclusive* lock excludes readers and writers/deleters alike, so concurrent requests
        against the same community serialize instead of racing each other.

        Existence is checked once before opening and once again after the lock is held: the
        first check can race a concurrent create/delete of the same file between the check and
        the `open` call, so only the second, lock-protected check is authoritative - a caller
        that skipped it could still open a file a concurrent delete removes moments later.

        Either way, the lock is always released. It is a plain `flock` on the config file
        itself, so it holds across both threads and processes without needing a separate lock
        file - but it is advisory and POSIX-only: it only excludes other code that goes through
        this same method, and it is not available on Windows.
        """
        path = self._community_path(slug)
        if not path.exists():
            raise ResourceNotFoundError(f"Community {slug!r} not found")

        file_mode = "r+" if writable else "r"
        lock_flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH

        with path.open(file_mode, encoding="utf-8") as handle:
            fcntl.flock(handle, lock_flag)
            try:
                if not path.exists():
                    raise ResourceNotFoundError(f"Community {slug!r} not found")
                yield handle
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @contextmanager
    def _open_community_config(self, slug: str, mode: Literal["read", "write"]) -> Generator[CofyAPISettings]:
        """Open a community's config for either a read or a read-modify-write.

        `mode="read"` takes a shared lock (see `_locked_file`) and writes nothing back.

        `mode="write"` takes an exclusive lock. If the block completes normally, the (possibly
        mutated) config is written back automatically; if it raises - e.g. a not-found or
        already-exists error - nothing is written.
        """
        with self._locked_file(slug, exclusive=mode == "write", writable=mode == "write") as handle:
            loaded = yaml.safe_load(handle)
            if not isinstance(loaded, dict):
                # `safe_load` of an empty or all-comments file returns `None`, which used to be
                # quietly turned into `{}` here - every field defaults, so that validated as a
                # legitimate blank community instead of surfacing a truncated file (e.g. from a
                # crash mid-write) as the corruption it actually is.
                raise ValueError(f"Community config at {self._community_path(slug)} must be a YAML mapping")

            config = CofyAPISettings.model_validate(loaded)
            yield config

            if mode == "write":
                # Serialize before truncating, so a dump that raises leaves the previous
                # contents alone instead of emptying the file.
                dumped = self._serialize(config)
                handle.seek(0)
                handle.truncate()
                handle.write(dumped)
                # Flush inside the lock: the write is buffered and the lock is released before
                # the handle is closed, so without this the next reader could take the lock and
                # still see the truncated file.
                handle.flush()
                os.fsync(handle.fileno())
