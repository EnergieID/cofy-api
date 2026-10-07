from __future__ import annotations

from ..auth.access import Action, Subject
from ..auth.user import User
from .policy import Policy


class CommunityPolicy(Policy):
    """The rules for communities themselves, which differ in two places: listing them takes being able to see one,
    and deleting one is not part of managing it."""

    def all(self) -> bool:
        return any(self.user.can(Action.read, Subject.community, slug) for slug in self.user.communities())

    def delete(self) -> bool:
        # Asked outside any one community, where only a system admin may write communities.
        return self.user.can(Action.write, Subject.community, None)

    @staticmethod
    def scope(user: User, slugs: list[str]) -> list[str]:
        """The communities among *slugs* that *user* may see."""
        return [slug for slug in slugs if user.can(Action.read, Subject.community, slug)]
