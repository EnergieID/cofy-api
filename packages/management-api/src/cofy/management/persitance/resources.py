from __future__ import annotations

from abc import ABC, abstractmethod

from cofy.api import ResourceSettings


class ResourcesPersistence(ABC):
    @abstractmethod
    def all(self, slug: str) -> list[ResourceSettings]:
        """List all resources for a community."""

    @abstractmethod
    def get(self, slug: str, name: str) -> ResourceSettings:
        """Get one resource by community slug and name."""

    @abstractmethod
    def create(self, slug: str, resource: ResourceSettings) -> ResourceSettings:
        """Create one resource for a community."""

    @abstractmethod
    def replace(self, slug: str, name: str, resource: ResourceSettings) -> ResourceSettings:
        """Replace one resource for a community.

        This is a *full* replace of a payload built from a read whose secrets were masked, so
        implementations must call `cofy.api.restore_masked_secrets` against the resource being
        replaced, inside whatever lock guards the write.
        """

    @abstractmethod
    def delete(self, slug: str, name: str) -> None:
        """Delete one resource for a community."""
