import builtins
import logging
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Annotated

from fastapi import Query

from ..model import Member
from ..source import MemberSource

LOGGER = logging.getLogger(__name__)

PAGE_SIZE = 50


class MembersFileSource(MemberSource[Member]):
    def __init__(
        self,
        file_path: str,
        load_from_file: Callable[[Path], dict[str, Member]],
        page_size: int = PAGE_SIZE,
        logger: logging.Logger = LOGGER,
    ):
        self.file_path = Path(file_path)
        self.load_from_file = load_from_file
        self.page_size = page_size
        self._lock = RLock()
        self._file_signature: tuple[int, int] | None = None
        self._members_by_id: dict[str, Member] = {}
        self._sorted_ids: list[str] = []
        self._members_by_activation_code: dict[str, Member] = {}
        self._maybe_reload(force=True)

    @property
    def response_model(self) -> type:
        return Member

    def list(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
    ) -> builtins.list[Member]:
        self._maybe_reload()
        start = (page - 1) * self.page_size
        end = start + self.page_size
        return [self._members_by_id[mid] for mid in self._sorted_ids[start:end]]

    def get(self, member_id: str) -> Member | None:
        self._maybe_reload()
        return self._members_by_id.get(member_id)

    def verify(self, activation_code: str) -> Member | None:
        self._maybe_reload()
        return self._members_by_activation_code.get(activation_code)

    def _maybe_reload(self, *, force: bool = False) -> None:
        signature = self._get_file_signature()
        if not force and signature == self._file_signature:
            return

        # use a lock to block if another thread is already reloading
        with self._lock:
            signature = self._get_file_signature()
            if not force and signature == self._file_signature:
                return

            if signature is None:
                return

            try:
                members = self.load_from_file(self.file_path)
            except Exception:
                LOGGER.exception("Failed to reload members from %s", self.file_path)
                return

            self._members_by_id = members
            self._sorted_ids = sorted(members.keys())
            self._members_by_activation_code = {
                member.activation_code: member for member in members.values() if member.activation_code is not None
            }
            self._file_signature = signature
            LOGGER.info("Loaded %s members from %s", len(members), self.file_path)

    def _get_file_signature(self) -> tuple[int, int] | None:
        try:
            stat = self.file_path.stat()
        except FileNotFoundError:
            return None
        return (stat.st_mtime_ns, stat.st_size)
