from typing import TYPE_CHECKING, Annotated, Literal

import narwhals as nw
from pydantic import Field, NonNegativeFloat

from cofy.api import BaseSettingsModel, FromSettingsMixin
from cofy.modules.timeseries import TimeseriesSource, TimeseriesSourceSettings

if TYPE_CHECKING:
    from .clusters import AccCluster, AccClusterSettings

    # Published at runtime by finalize(); the base classes are the static stand-ins.
    AnyTimeseriesSourceSettings = TimeseriesSourceSettings
    AnyAccClusterSettings = AccClusterSettings

Role = Literal["consumer", "producer", "prosumer"]


class AccMemberSettings(BaseSettingsModel):
    source: 'Annotated[AnyTimeseriesSourceSettings | AnyAccClusterSettings, Field(discriminator="type")]'


class AccMember(FromSettingsMixin):
    def __init__(self, source: "TimeseriesSource | AccCluster"):
        """A member of an ACC cluster.

        Args:
            source: Where the member's net volume comes from: a connection's source, or a nested cluster.
        """
        self.source = source

    def participating(self, volume: nw.Expr) -> nw.Expr:
        """The part of the net volume that takes part in the cluster's matching."""
        return volume

    def consumption(self, volume: nw.Expr) -> nw.Expr:
        """Consumption that the cluster can match."""
        return self.participating(volume).clip(lower_bound=0)

    def production(self, volume: nw.Expr) -> nw.Expr:
        """Production that the cluster can match."""
        return (-self.participating(volume)).clip(lower_bound=0)

    def residual(self, volume: nw.Expr) -> nw.Expr:
        """The net volume this member passes on to the cluster's parent, matched and unmatched."""
        return self.participating(volume)


def by_role(volume: nw.Expr, role: Role) -> nw.Expr:
    """The part of the net volume that fits the role, a prosumer's role following its sign."""
    if role == "consumer":
        return volume.clip(lower_bound=0)
    if role == "producer":
        return volume.clip(upper_bound=0)
    return volume


class AccPoolMemberSettings(AccMemberSettings):
    type: Literal["acc_pool_member"] = "acc_pool_member"


class AccPoolMember(AccMember, settings=AccPoolMemberSettings):
    """A pool member, whose whole volume takes part."""


class AccPriorityMemberSettings(AccMemberSettings):
    type: Literal["acc_priority_member"] = "acc_priority_member"
    role: Role = "prosumer"


class AccPriorityMember(AccMember, settings=AccPriorityMemberSettings):
    def __init__(self, role: Role = "prosumer", **kwargs):
        """A producer priority member, of which only the volume fitting its role takes part."""
        super().__init__(**kwargs)
        self.role = role

    def participating(self, volume: nw.Expr) -> nw.Expr:
        return by_role(volume, self.role)


class AccCapacityMemberSettings(AccMemberSettings):
    type: Literal["acc_capacity_member"] = "acc_capacity_member"
    role: Role = "prosumer"
    consumption_capacity_kwh: NonNegativeFloat | None = None
    production_capacity_kwh: NonNegativeFloat | None = None


class AccCapacityMember(AccMember, settings=AccCapacityMemberSettings):
    def __init__(
        self,
        role: Role = "prosumer",
        consumption_capacity_kwh: float | None = None,
        production_capacity_kwh: float | None = None,
        **kwargs,
    ):
        """A capacity priority member, of which the volume fitting its role takes part, matched up to its capacities per timestamp.

        Args:
            role: Which side of its volume takes part.
            consumption_capacity_kwh: Most consumption matched per timestamp, unlimited if None.
            production_capacity_kwh: Most production matched per timestamp, unlimited if None.
        """
        super().__init__(**kwargs)
        self.role = role
        self.consumption_capacity_kwh = consumption_capacity_kwh
        self.production_capacity_kwh = production_capacity_kwh

    def participating(self, volume: nw.Expr) -> nw.Expr:
        return by_role(volume, self.role)

    def consumption(self, volume: nw.Expr) -> nw.Expr:
        return super().consumption(volume).clip(upper_bound=self.consumption_capacity_kwh)

    def production(self, volume: nw.Expr) -> nw.Expr:
        return super().production(volume).clip(upper_bound=self.production_capacity_kwh)


class AccShareMemberSettings(BaseSettingsModel):
    type: Literal["acc_share_member"] = "acc_share_member"
    # ACC doesn't support nesting clusters in a producer share cluster, so members are sources only.
    source: "AnyTimeseriesSourceSettings"
    role: Role = "prosumer"
    share_ratio: float = Field(default=1.0, ge=0, le=1)


class AccShareMember(AccMember, settings=AccShareMemberSettings):
    def __init__(self, source: TimeseriesSource, role: Role = "prosumer", share_ratio: float = 1.0):
        """A producer share member, of which the share of its volume fitting its role takes part.

        Args:
            source: Source of the member's net volumes.
            role: Which side of its volume takes part.
            share_ratio: Share of its volume the member brings into the cluster.
        """
        super().__init__(source=source)
        self.role = role
        self.share_ratio = share_ratio

    def participating(self, volume: nw.Expr) -> nw.Expr:
        return by_role(volume * self.share_ratio, self.role)

    def residual(self, volume: nw.Expr) -> nw.Expr:
        # unlike the other cluster types, ACC passes on a producer share member's whole volume
        return volume
