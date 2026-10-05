from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import yaml

from ....auth.access import UserRecord, UsersFile
from .store import FileStore


class UsersFileStore(FileStore[UsersFile]):
    """The users file, which lists everyone who may do something; without it, nobody may."""

    document = UsersFile

    def __init__(self, path: Path):
        self.path = path

    def _serialize(self, document: UsersFile) -> str:
        # Validated again as a whole, as it will be read back, so a write can't store a file that can't be read.
        UsersFile.model_validate(document.model_dump())
        # Each person without the fields they leave at their defaults, as someone would write them by hand.
        listed = [user.model_dump(mode="json", exclude_defaults=True) for user in document.users]
        return yaml.safe_dump({"users": listed}, sort_keys=False)

    @contextmanager
    def _open_users(self, mode: Literal["read", "write"]) -> Generator[UsersFile]:
        """The users file for a read or a read-modify-write; a write creates it if it is missing."""
        if mode == "read" and not self.path.exists():
            yield UsersFile()
            return
        with self._open_document(self.path, mode, create=mode == "write") as users:
            yield users

    @staticmethod
    def _find(users: UsersFile, email: str) -> UserRecord | None:
        return next((user for user in users.users if user.has_email(email)), None)
