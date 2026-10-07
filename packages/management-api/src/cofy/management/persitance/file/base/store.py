import fcntl
import os
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import IO, ClassVar, Generic, Literal, TypeVar

import yaml
from pydantic import BaseModel

from ....errors import ManagementError, ResourceNotFoundError

DATA_DIR_ENV_VAR = "COFY_MANAGEMENT_DATA_DIR"


def data_dir() -> Path:
    """Where the management API keeps everything it stores, each kind in a subdirectory of its own.

    There is no built-in default: this is a deployment's writable state, not something the
    library can guess at or ship a sample of, so the environment variable is required.
    """
    configured = os.environ.get(DATA_DIR_ENV_VAR)
    if not configured:
        raise RuntimeError(f"{DATA_DIR_ENV_VAR} must be set to a writable directory for the management API's data")
    return Path(configured)


Document = TypeVar("Document", bound=BaseModel)


class FileStore(ABC, Generic[Document]):
    """YAML documents on disk, each read and written whole while a lock is held on its file."""

    document: ClassVar[type[BaseModel]]
    """The model a document is validated as."""

    def _parse(self, loaded: dict, path: Path) -> Document:
        return self.document.model_validate(loaded)  # ty: ignore[invalid-return-type]

    @abstractmethod
    def _serialize(self, document: Document) -> str:
        """The on-disk YAML form of *document* - the one place a validated document is turned back
        into text, so every write path stays byte-for-byte consistent instead of quietly drifting
        apart."""

    def _not_found(self, path: Path) -> ManagementError:
        """The error for a document that doesn't exist."""
        return ResourceNotFoundError(f"{path.name} not found")

    @contextmanager
    def _locked_file(
        self, path: Path, *, exclusive: bool, writable: bool = False, create: bool = False
    ) -> Generator[IO[str]]:
        """Open the file at *path* and hold a lock on it for the duration of the block.

        A *shared* lock (`exclusive=False`) excludes a concurrent exclusive lock (a write or a
        delete) - so a reader is never handed a document mid-write, or one that has just been
        deleted - without excluding other concurrent shared holders (other reads). An
        *exclusive* lock excludes readers and writers/deleters alike, so concurrent requests
        against the same document serialize instead of racing each other.

        Unless *create* makes a missing file, existence is checked once before opening and once
        again after the lock is held: the first check can race a concurrent create/delete of the
        same file between the check and the `open` call, so only the second, lock-protected
        check is authoritative - a caller that skipped it could still open a file a concurrent
        delete removes moments later.

        Either way, the lock is always released. It is a plain `flock` on the file itself, so it
        holds across both threads and processes without needing a separate lock file - but it is
        advisory and POSIX-only: it only excludes other code that goes through this same method,
        and it is not available on Windows.
        """
        if create:
            path.parent.mkdir(parents=True, exist_ok=True)
            # Opened through `os.open`, as `open`'s modes can't create a file without truncating it.
            handle = os.fdopen(os.open(path, os.O_RDWR | os.O_CREAT, 0o644), "r+", encoding="utf-8")
        elif not path.exists():
            raise self._not_found(path)
        else:
            handle = path.open("r+" if writable else "r", encoding="utf-8")

        with handle:
            fcntl.flock(handle, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                if not path.exists():
                    raise self._not_found(path)
                yield handle
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @contextmanager
    def _open_document(
        self, path: Path, mode: Literal["read", "write"], *, create: bool = False
    ) -> Generator[Document]:
        """Open the document at *path* for either a read or a read-modify-write.

        `mode="read"` takes a shared lock (see `_locked_file`) and writes nothing back.

        `mode="write"` takes an exclusive lock. If the block completes normally, the (possibly
        mutated) document is written back automatically; if it raises - e.g. a not-found or
        already-exists error - nothing is written. With *create*, a missing file is created and
        starts out as an empty document.
        """
        created = create and not path.exists()
        with self._locked_file(path, exclusive=mode == "write", writable=mode == "write", create=create) as handle:
            loaded = yaml.safe_load(handle)
            if loaded is None and created:
                loaded = {}
            if not isinstance(loaded, dict):
                # `safe_load` of an empty or all-comments file returns `None`, which used to be
                # quietly turned into `{}` here - every field defaults, so that validated as a
                # legitimate blank document instead of surfacing a truncated file (e.g. from a
                # crash mid-write) as the corruption it actually is.
                raise ValueError(f"The file at {path} must be a YAML mapping")

            document = self._parse(loaded, path)
            yield document

            if mode == "write":
                # Serialize before truncating, so a dump that raises leaves the previous
                # contents alone instead of emptying the file.
                dumped = self._serialize(document)
                handle.seek(0)
                handle.truncate()
                handle.write(dumped)
                # Flush inside the lock: the write is buffered and the lock is released before
                # the handle is closed, so without this the next reader could take the lock and
                # still see the truncated file.
                handle.flush()
                os.fsync(handle.fileno())
