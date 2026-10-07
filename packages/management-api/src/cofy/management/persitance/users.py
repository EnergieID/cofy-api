from __future__ import annotations

from abc import ABC, abstractmethod

from ..auth.access import Identity, UserRecord


class UsersPersistence(ABC):
    """Everyone who may do something, as far as logging in is concerned: who someone is, and binding them."""

    @abstractmethod
    def match(self, identity: Identity) -> UserRecord | None:
        """The person *identity* is, if they are listed."""

    @abstractmethod
    def bind(self, identity: Identity) -> None:
        """Bind *identity* to the person still waiting for its first login, if there is one."""
