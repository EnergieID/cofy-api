import logging
from collections.abc import Generator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Literal

import yaml

from ....auth.access import UserRecord, UsersFile
from ....errors import StoredDataInvalidError
from .store import FileStore

logger = logging.getLogger(__name__)


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
        with ExitStack() as stack:
            try:
                users = stack.enter_context(self._open_document(self.path, mode, create=mode == "write"))
            except (ValueError, yaml.YAMLError) as exc:
                # Every request and every login reads this file, so what's wrong with it goes to the log, for whoever
                # keeps it, and not into a response for whoever happened to ask.
                logger.error("The users file at %s can't be read: %s", self.path, exc)
                raise StoredDataInvalidError("Who may do what can't be read; it has to be fixed on the server") from exc
            yield users

    @staticmethod
    def _find(users: UsersFile, email: str) -> UserRecord | None:
        return next((user for user in users.users if user.has_email(email)), None)
