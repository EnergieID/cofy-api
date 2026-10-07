from __future__ import annotations

from abc import ABC, abstractmethod

from ..auth.access import Grant


class GrantsPersistence(ABC):
    """The roles granted in each community, to the people they are granted to."""

    @abstractmethod
    def all(self, slug: str) -> list[Grant]:
        """List the grants in a community."""

    @abstractmethod
    def get(self, slug: str, email: str) -> Grant:
        """Get the grant to *email* in a community."""

    @abstractmethod
    def create(self, slug: str, grant: Grant) -> Grant:
        """Grant a role in a community, failing if that person already has one there."""

    @abstractmethod
    def replace(self, slug: str, email: str, grant: Grant) -> Grant:
        """Replace the grant to *email* in a community."""

    @abstractmethod
    def delete(self, slug: str, email: str) -> None:
        """Revoke the grant to *email* in a community."""

    @abstractmethod
    def delete_all(self, slug: str) -> None:
        """Revoke every grant in a community, for when it is deleted."""
