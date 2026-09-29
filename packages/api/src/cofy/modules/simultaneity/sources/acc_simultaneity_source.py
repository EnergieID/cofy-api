from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal

import narwhals as nw

from cofy.modules.timeseries import Timeseries, TimeseriesSourceSettings

from ..acc.clusters import AccCluster
from .base_simultaneity_source import BaseSimultaneitySource

if TYPE_CHECKING:
    from ..acc.clusters import AccClusterSettings

    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyAccClusterSettings = AccClusterSettings


class AccSimultaneitySourceSettings(TimeseriesSourceSettings):
    type: Literal["acc_simultaneity"] = "acc_simultaneity"
    # Unresolved until cofy.api.finalize() publishes the discriminated unions.
    cluster: "AnyAccClusterSettings"


class AccSimultaneitySource(BaseSimultaneitySource, settings=AccSimultaneitySourceSettings):
    def __init__(self, cluster: AccCluster):
        """Simultaneity of a tree of clusters following ACC's concurrency matching, as a percentage per timestamp.

        This is the consumption as a percentage of the production, counting only volumes the clusters can match:
        all volume matched anywhere in the tree, plus what the root cluster could still match on either side.

        Args:
            cluster: The root cluster.
        """
        super().__init__(cluster.sources())
        self.cluster = cluster

    def volumes(self, results: Sequence[Timeseries]) -> nw.DataFrame:
        columns = {id(source): f"member_{i}" for i, source in enumerate(self.sources)}
        wide = nw.concat(
            [
                ts.frame.select("timestamp", "value").with_columns(member=nw.lit(columns[id(source)]))
                for source, ts in zip(self.sources, results, strict=True)
            ]
        ).pivot(on="member", index="timestamp", values="value", aggregate_function="sum")
        # a source without data at a timestamp has no volume there
        wide = wide.with_columns(
            nw.col(c).fill_null(0.0) if c in wide.columns else nw.lit(0.0).alias(c) for c in columns.values()
        )

        volumes = self.cluster.volumes(lambda source: nw.col(columns[id(source)]))
        # all that is matched in the tree, plus what the root cluster could still match on either side
        nested_matched = volumes.matched_in_tree - volumes.matched
        return wide.select(
            "timestamp",
            consumption=nested_matched + volumes.consumption,
            production=nested_matched + volumes.production,
        )
