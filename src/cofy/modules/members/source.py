import builtins
from abc import ABC, abstractmethod

from .model import Member


class MemberSource[T](ABC):
    @abstractmethod
    def list(
        self,
    ) -> builtins.list[T]:
        """List all members."""

    @abstractmethod
    def get(self, member_id: str) -> T | None:
        """Return a single member by ID."""

    @abstractmethod
    def verify(self, activation_code: str) -> T | None:
        """Return member matching the activation code."""

    @property
    def response_model(self) -> type:
        """The response model of the source."""
        return Member
