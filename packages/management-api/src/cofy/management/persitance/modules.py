from __future__ import annotations

from abc import ABC, abstractmethod

from cofy.api.module import ModuleSettings


class ModulesPersistence(ABC):
    @abstractmethod
    def all(self, slug: str) -> list[ModuleSettings]:
        """List all modules for a community."""

    @abstractmethod
    def get(self, slug: str, module_type: str, name: str) -> ModuleSettings:
        """Get one module by community slug, type and name."""

    @abstractmethod
    def create(self, slug: str, module: ModuleSettings) -> ModuleSettings:
        """Create one module for a community."""

    @abstractmethod
    def replace(self, slug: str, module_type: str, name: str, module: ModuleSettings) -> ModuleSettings:
        """Replace one module for a community.

        This is a *full* replace of a payload built from a read whose secrets were masked, so
        implementations must call `cofy.api.restore_masked_secrets` against the module being
        replaced, inside whatever lock guards the write.
        """

    @abstractmethod
    def delete(self, slug: str, module_type: str, name: str) -> None:
        """Delete one module for a community."""
