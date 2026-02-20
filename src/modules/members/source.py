from abc import ABC, abstractmethod

from src.modules.members.model import Member


class MemberSource[T](ABC):
    @abstractmethod
    def list(
        self,
        email: str | None = None,
    ) -> list[T]:
        """List all members."""

    @abstractmethod
    def verify(self, activation_code: str) -> T | None:
        """Return member matching the activation code."""

    @property
    def response_model(self) -> type:
        """The response model of the source."""
        return Member
