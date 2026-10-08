from __future__ import annotations

from abc import ABC, abstractmethod

from cofy.api import TokenInfo


class TokensPersistence(ABC):
    @abstractmethod
    def all(self, slug: str) -> list[TokenInfo]:
        """List all API tokens for a community."""

    @abstractmethod
    def get(self, slug: str, name: str) -> TokenInfo:
        """Get one API token by community slug and name."""

    @abstractmethod
    def create(self, slug: str, token: TokenInfo) -> TokenInfo:
        """Create one API token for a community."""

    @abstractmethod
    def replace(self, slug: str, name: str, token: TokenInfo) -> TokenInfo:
        """Replace one API token for a community."""

    @abstractmethod
    def delete(self, slug: str, name: str) -> None:
        """Delete one API token for a community."""
