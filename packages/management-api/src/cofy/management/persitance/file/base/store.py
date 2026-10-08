import fcntl
import os
import tempfile
from abc import ABC, abstractmethod
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import ClassVar, Generic, Literal, TypeVar

import yaml
from pydantic import BaseModel

from ....errors import ManagementError, ResourceNotFoundError

DATA_DIR_ENV_VAR = "COFY_MANAGEMENT_DATA_DIR"


def data_dir() -> Path:
    """Where the management API keeps what it stores other than the community configs, each kind in a subdirectory.

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

    @staticmethod
    def _lock_path(path: Path) -> Path:
        """The hidden lock file beside the document at *path*."""
        return path.with_name(f".{path.name}.lock")

    @contextmanager
    def _locked(self, path: Path, *, exclusive: bool, create: bool = False) -> Generator[None]:
        """Hold a lock on the document at *path* for the duration of the block.

        A *shared* lock (`exclusive=False`) excludes a concurrent exclusive lock (a write or a
        delete) - so a reader is never handed a document that has just been deleted - without
        excluding other concurrent shared holders (other reads). An *exclusive* lock excludes
        readers and writers/deleters alike, so concurrent requests against the same document
        serialize instead of racing each other.

        The lock is taken on a lock file beside the document rather than on the document itself,
        because a write replaces the document with a new file (see `_write`): a lock on the old one
        would no longer guard anything. The lock file outlives a deleted document, as removing it
        could leave a waiter holding a lock on a file nobody else locks.

        Unless *create* allows a missing document, existence is checked once before locking and
        once again after the lock is held: the first check keeps a request for a document that
        doesn't exist from leaving a lock file behind, but can race a concurrent create/delete, so
        only the second, lock-protected check is authoritative.

        It is a plain `flock`, so it holds across both threads and processes - but it is advisory
        and POSIX-only: it only excludes other code that goes through this same method, and it is
        not available on Windows. Code that only reads, and doesn't take it, still never sees a
        half-written document, as a write is a rename.
        """
        if not create and not path.exists():
            raise self._not_found(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock_path(path).open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
            try:
                if not create and not path.exists():
                    raise self._not_found(path)
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @staticmethod
    def _write(path: Path, text: str) -> None:
        """Replace the document at *path* with *text* in one step: written to a temporary file beside it, then renamed
        over it, so anyone opening it sees either the previous document or this one, never part of it."""
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                # On disk before the rename, or a crash could leave the new name on an empty file.
                handle.flush()
                os.fsync(handle.fileno())
            # `mkstemp` makes the file private to this user; what reads it - the runner - may run as another.
            os.chmod(temporary, 0o644)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    @contextmanager
    def _open_document(
        self, path: Path, mode: Literal["read", "write"], *, create: bool = False
    ) -> Generator[Document]:
        """Open the document at *path* for either a read or a read-modify-write.

        `mode="read"` takes a shared lock (see `_locked`) and writes nothing back.

        `mode="write"` takes an exclusive lock. If the block completes normally, the (possibly
        mutated) document is written back automatically; if it raises - e.g. a not-found or
        already-exists error - nothing is written. With *create*, a missing file is created and
        starts out as an empty document.
        """
        with self._locked(path, exclusive=mode == "write", create=create):
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
            if not isinstance(loaded, dict):
                # `safe_load` of an empty or all-comments file returns `None`, which must not be
                # quietly turned into `{}`: every field defaults, so that would validate as a
                # legitimate blank document instead of surfacing a damaged file as what it is.
                raise ValueError(f"The file at {path} must be a YAML mapping")

            document = self._parse(loaded, path)
            yield document

            if mode == "write":
                self._write(path, self._serialize(document))
