from __future__ import annotations

from abc import ABC, abstractmethod

from cofy.api.cofy_api import CofyAPISettings


class CommunitiesPersistence(ABC):
    """CRUD over the communities themselves, as distinct from the modules inside them.

    A community's stored config holds its modules too, but those are managed through
    `ModulesPersistence`. Implementations of `update` must leave the stored modules - and the
    stored `auth` block - exactly as they were.
    """

    @abstractmethod
    def all(self) -> list[tuple[str, CofyAPISettings]]:
        """List every community as `(slug, settings)`."""

    @abstractmethod
    def get(self, slug: str) -> CofyAPISettings:
        """Get one community's settings."""

    @abstractmethod
    def create(self, slug: str, settings: CofyAPISettings) -> CofyAPISettings:
        """Create a community, failing if the slug is taken."""

    @abstractmethod
    def update(self, slug: str, settings: CofyAPISettings) -> CofyAPISettings:
        """Update one community's own settings, leaving its modules and auth untouched."""

    @abstractmethod
    def delete(self, slug: str) -> None:
        """Delete a community and everything configured in it."""
