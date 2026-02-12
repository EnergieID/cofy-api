from abc import ABC, abstractmethod

from modules.members.model import Member


class MemberSource[T: Member](ABC):
    @abstractmethod
    def list(self) -> list[T]:
        """List all members."""
