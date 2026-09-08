import fcntl
from collections.abc import Generator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from typing import Literal

import yaml
from cofy.api.cofy_api import CofyAPISettings

from ...errors import ResourceNotFoundError

DEFAULT_BASE_PATH = Path(str(resources.files("cofy.management.persitance.file") / "data"))


class FilePersistence:
    def __init__(self, base_path: Path = DEFAULT_BASE_PATH):
        self.base_path = base_path

    def _community_path(self, slug: str) -> Path:
        return self.base_path / f"{slug}.yaml"

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
                    handle.seek(0)
                    handle.truncate()
                    yaml.safe_dump(
                        config.model_dump(exclude_none=True, polymorphic_serialization=True, round_trip=True),
                        handle,
                        sort_keys=True,
                    )
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)
