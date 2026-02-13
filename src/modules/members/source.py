from abc import ABC, abstractmethod

from src.modules.members.model import Member


class MemberSource[T](ABC):
    @abstractmethod
    def list(self) -> list[T]:
        """List all members."""

    @property
    def response_model(self) -> type:
        """The response model of the source."""
        return Member
