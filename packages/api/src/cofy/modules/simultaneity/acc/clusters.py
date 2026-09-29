import operator
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import reduce
from typing import Generic, Literal, TypeVar

import narwhals as nw
from pydantic import Field

from cofy.api import BaseSettingsModel, FromSettingsMixin
from cofy.modules.timeseries import TimeseriesSource

from .members import (
    AccCapacityMember,
    AccCapacityMemberSettings,
    AccMember,
    AccPoolMember,
    AccPoolMemberSettings,
    AccPriorityMember,
    AccPriorityMemberSettings,
    AccShareMember,
    AccShareMemberSettings,
)


@dataclass
class ClusterVolumes:
    """Expressions for the volumes of a cluster per timestamp."""

    consumption: nw.Expr
    """Consumption the cluster can match."""
    production: nw.Expr
    """Production the cluster can match."""
    matched: nw.Expr
    """Volume matched by the cluster itself."""
    matched_in_tree: nw.Expr
    """Volume matched by the cluster and all of its nested clusters."""
    residual: nw.Expr
    """Net volume the cluster passes on to its parent."""


class AccClusterSettings(BaseSettingsModel):
    type: Literal["acc_cluster"] = "acc_cluster"


M = TypeVar("M", bound=AccMember)


class AccCluster(FromSettingsMixin, Generic[M], settings=AccClusterSettings, abstract=True):
    def __init__(self, members: Sequence[M]):
        """A cluster of ACC's concurrency matching, which matches the consumption and production of its members."""
        self.members = members

    def sources(self) -> list[TimeseriesSource]:
        """The sources of all connections in the cluster and its nested clusters."""
        sources = []
        for member in self.members:
            if member.cluster is not None:
                sources.extend(member.cluster.sources())
            elif member.source is not None:
                sources.append(member.source)
        return sources

    def volumes(self, volume_of: Callable[[TimeseriesSource], nw.Expr]) -> ClusterVolumes:
        """The cluster's volumes, given the net volume expression of each connection's source."""
        consumption, production, residual, nested_matched = [], [], [], []
        for member in self.members:
            if member.cluster is not None:
                nested = member.cluster.volumes(volume_of)
                volume = nested.residual
                nested_matched.append(nested.matched_in_tree)
            elif member.source is not None:
                volume = volume_of(member.source)
            consumption.append(member.consumption(volume))
            production.append(member.production(volume))
            residual.append(member.residual(volume))

        total_consumption = _sum(consumption)
        total_production = _sum(production)
        matched = nw.when(total_consumption < total_production).then(total_consumption).otherwise(total_production)
        return ClusterVolumes(
            consumption=total_consumption,
            production=total_production,
            matched=matched,
            matched_in_tree=_sum([matched, *nested_matched]),
            # matched volumes cancel out between consumers and producers, so what remains is the net participating volume
            residual=_sum(residual),
        )


def _sum(exprs: list[nw.Expr]) -> nw.Expr:
    # plain addition rather than sum_horizontal, which fails on pandas for expressions sharing an output name
    return reduce(operator.add, exprs)


class AccPoolClusterSettings(AccClusterSettings):
    type: Literal["pool"] = "pool"
    members: list[AccPoolMemberSettings] = Field(min_length=1)


class AccPoolCluster(AccCluster[AccPoolMember], settings=AccPoolClusterSettings):
    """A cluster matching all consumption and production of its members pro rata."""


class AccProducerPriorityClusterSettings(AccClusterSettings):
    type: Literal["producer_priority"] = "producer_priority"
    members: list[AccPriorityMemberSettings] = Field(min_length=1)


class AccProducerPriorityCluster(AccCluster[AccPriorityMember], settings=AccProducerPriorityClusterSettings):
    """A cluster matching consumption to producers in order of priority.

    The priority only decides which producers are matched, not how much is matched in total, so it has no
    influence on simultaneity and isn't configured.
    """


class AccCapacityPriorityClusterSettings(AccClusterSettings):
    type: Literal["capacity_priority"] = "capacity_priority"
    members: list[AccCapacityMemberSettings] = Field(min_length=1)


class AccCapacityPriorityCluster(AccCluster[AccCapacityMember], settings=AccCapacityPriorityClusterSettings):
    """A producer priority cluster, matching each member up to its capacities.

    As with producer priority, the priority has no influence on simultaneity and isn't configured.
    """


class AccProducerShareClusterSettings(AccClusterSettings):
    type: Literal["producer_share"] = "producer_share"
    members: list[AccShareMemberSettings] = Field(min_length=1)


class AccProducerShareCluster(AccCluster[AccShareMember], settings=AccProducerShareClusterSettings):
    """A cluster distributing the shared production of its producers over its consumers.

    ACC matches all shared production, also beyond what consumers consume, but only the consumed part counts
    towards simultaneity.
    """
