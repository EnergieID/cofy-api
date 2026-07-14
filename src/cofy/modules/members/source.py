import builtins
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from cofy.api.from_settings_mixin import BaseSettingsModel, FromSettingsMixin

from .model import Member

T = TypeVar("T")


class MemberSourceSettings(BaseSettingsModel):
    type: str = "member_source"


class MemberSource(FromSettingsMixin, ABC, Generic[T], settings=MemberSourceSettings):
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
