import builtins
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from .model import Member

T = TypeVar("T")


class MemberSource(ABC, Generic[T]):
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
