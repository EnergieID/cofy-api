from abc import ABC, abstractmethod


class MemberSource(ABC):
    @abstractmethod
    def list(self) -> list:
        """List all members."""
