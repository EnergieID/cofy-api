from __future__ import annotations

from abc import ABC, abstractmethod

from cofy.api import SecretSettings


class SecretsPersistence(ABC):
    @abstractmethod
    def all(self, slug: str) -> list[SecretSettings]:
        """List all secrets for a community."""

    @abstractmethod
    def get(self, slug: str, name: str) -> SecretSettings:
        """Get one secret by community slug and name."""

    @abstractmethod
    def create(self, slug: str, secret: SecretSettings) -> SecretSettings:
        """Create one secret for a community."""

    @abstractmethod
    def replace(self, slug: str, name: str, secret: SecretSettings) -> SecretSettings:
        """Replace one secret for a community, value and all."""

    @abstractmethod
    def delete(self, slug: str, name: str) -> None:
        """Delete one secret for a community."""
