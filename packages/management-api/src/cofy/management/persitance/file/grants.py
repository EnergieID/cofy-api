from ...auth.access import Grant, UserRecord, UsersFile
from ...errors import ResourceAlreadyExistsError, ResourceNotFoundError
from ..grants import GrantsPersistence
from .base import UsersFileStore


class FileGrantsPersistence(UsersFileStore, GrantsPersistence):
    """Grants, kept in the users file with the people they are granted to."""

    def all(self, slug: str) -> list[Grant]:
        with self._open_users("read") as users:
            return [self._grant(user, slug) for user in users.users if slug in user.grants]

    def get(self, slug: str, email: str) -> Grant:
        with self._open_users("read") as users:
            return self._grant(self._grantee(users, slug, email), slug)

    def create(self, slug: str, grant: Grant) -> Grant:
        with self._open_users("write") as users:
            user = self._find(users, str(grant.email))
            if user is None:
                user = UserRecord(email=grant.email)
                users.users.append(user)
            elif slug in user.grants:
                raise ResourceAlreadyExistsError(f"{str(grant.email)!r} already has a role in {slug!r}")
            user.grants[slug] = grant.role
            return self._grant(user, slug)

    def replace(self, slug: str, email: str, grant: Grant) -> Grant:
        with self._open_users("write") as users:
            user = self._grantee(users, slug, email)
            user.grants[slug] = grant.role
            return self._grant(user, slug)

    def delete(self, slug: str, email: str) -> None:
        with self._open_users("write") as users:
            self._revoke(users, self._grantee(users, slug, email), slug)

    def delete_all(self, slug: str) -> None:
        with self._open_users("write") as users:
            for user in [user for user in users.users if slug in user.grants]:
                self._revoke(users, user, slug)

    @staticmethod
    def _grant(user: UserRecord, slug: str) -> Grant:
        return Grant(email=user.email, role=user.grants[slug], bound=user.bound)

    def _grantee(self, users: UsersFile, slug: str, email: str) -> UserRecord:
        user = self._find(users, email)
        if user is None or slug not in user.grants:
            raise ResourceNotFoundError(f"Grant to {email!r} in {slug!r} not found")
        return user

    @staticmethod
    def _revoke(users: UsersFile, user: UserRecord, slug: str) -> None:
        del user.grants[slug]
        # Someone with no role left, and not a system admin, has nothing left to be listed for.
        if not user.grants and not user.system_admin:
            users.users.remove(user)
