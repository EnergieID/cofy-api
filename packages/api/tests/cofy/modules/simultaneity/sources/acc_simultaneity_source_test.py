import datetime as dt
import math

import pytest
from pydantic import ValidationError

from cofy.modules.simultaneity import (
    AccCapacityPriorityCluster,
    AccPoolCluster,
    AccProducerPriorityCluster,
    AccProducerShareCluster,
    AccSimultaneitySource,
    SimultaneitySource,
)
from cofy.modules.simultaneity.acc import (
    AccCapacityMember,
    AccCluster,
    AccPoolMember,
    AccPriorityMember,
    AccShareMember,
)
from cofy.modules.timeseries import TimeseriesSource

from ...timeseries.dummy_source import DummyTimeseriesSource
from ..fixed_source import QUARTER, START, FixedSource


async def fetch_values(cluster: AccCluster) -> list[float]:
    result = await AccSimultaneitySource(cluster).fetch_timeseries(START, START + dt.timedelta(hours=1), QUARTER)
    return [row["value"] for row in result.to_arr()]


def pool(*members: TimeseriesSource | AccCluster) -> AccPoolCluster:
    return AccPoolCluster(
        [
            AccPoolMember(cluster=member) if isinstance(member, AccCluster) else AccPoolMember(source=member)
            for member in members
        ]
    )


@pytest.mark.asyncio
async def test_pool_is_consumption_over_production():
    consumer = FixedSource([10.0, 5.0, 20.0])
    producer = FixedSource([-10.0, -10.0, -10.0])

    simple = await SimultaneitySource([consumer, producer]).fetch_timeseries(
        START, START + dt.timedelta(hours=1), QUARTER
    )

    assert await fetch_values(pool(consumer, producer)) == [100.0, 50.0, 200.0]
    assert [row["value"] for row in simple.to_arr()] == [100.0, 50.0, 200.0]


@pytest.mark.asyncio
async def test_nested_pools_match_like_one_pool():
    # the nested pool matches 4 and passes on 6 consumption, which the root matches with its 10 production
    nested = pool(FixedSource([10.0]), FixedSource([-4.0]))

    assert await fetch_values(pool(nested, FixedSource([-10.0]))) == [pytest.approx(10 / 14 * 100)]


@pytest.mark.asyncio
async def test_producer_priority_ignores_volume_outside_a_members_role():
    cluster = AccProducerPriorityCluster(
        [
            AccPriorityMember(source=FixedSource([10.0, 10.0]), role="consumer"),
            # the turbine's standby consumption and the consumer's own solar production don't take part
            AccPriorityMember(source=FixedSource([-20.0, 2.0]), role="producer"),
            AccPriorityMember(source=FixedSource([-3.0, -3.0]), role="consumer"),
        ]
    )

    assert await fetch_values(cluster) == [50.0, math.inf]


@pytest.mark.asyncio
async def test_prosumers_take_part_on_both_sides():
    cluster = AccProducerPriorityCluster(
        [
            AccPriorityMember(source=FixedSource([10.0, 10.0])),
            AccPriorityMember(source=FixedSource([-20.0, 10.0])),
            AccPriorityMember(source=FixedSource([-5.0, -5.0]), role="producer"),
        ]
    )

    assert await fetch_values(cluster) == [40.0, 400.0]


@pytest.mark.asyncio
async def test_capacity_priority_matches_up_to_capacities():
    cluster = AccCapacityPriorityCluster(
        [
            AccCapacityMember(source=FixedSource([10.0]), role="consumer", consumption_capacity_kwh=6),
            AccCapacityMember(source=FixedSource([4.0]), role="consumer"),
            AccCapacityMember(source=FixedSource([-20.0]), role="producer", production_capacity_kwh=8),
        ]
    )

    assert await fetch_values(cluster) == [pytest.approx(10 / 8 * 100)]


@pytest.mark.asyncio
async def test_producer_share_counts_only_shared_production():
    cluster = AccProducerShareCluster(
        [
            AccShareMember(source=FixedSource([-100.0]), role="producer", share_ratio=0.1),
            AccShareMember(source=FixedSource([5.0]), role="consumer"),
        ]
    )

    assert await fetch_values(cluster) == [50.0]


@pytest.mark.asyncio
async def test_producer_share_passes_on_unshared_production():
    # the shared 10 matches 5 consumption, and the pool matches its 30 consumption with the rest of the 100
    shared = AccProducerShareCluster(
        [
            AccShareMember(source=FixedSource([-100.0]), role="producer", share_ratio=0.1),
            AccShareMember(source=FixedSource([5.0]), role="consumer"),
        ]
    )

    assert await fetch_values(pool(shared, FixedSource([30.0]))) == [35.0]


@pytest.mark.asyncio
async def test_nested_cluster_takes_part_according_to_its_role():
    # the nested pool matches 4 and passes on 6 consumption, which its producer role in the root leaves out
    nested = pool(FixedSource([10.0]), FixedSource([-4.0]))
    cluster = AccProducerPriorityCluster(
        [
            AccPriorityMember(cluster=nested, role="producer"),
            AccPriorityMember(source=FixedSource([3.0]), role="consumer"),
            AccPriorityMember(source=FixedSource([-5.0]), role="producer"),
        ]
    )

    assert await fetch_values(cluster) == [pytest.approx(7 / 9 * 100)]


@pytest.mark.asyncio
async def test_missing_data_counts_as_no_volume():
    assert await fetch_values(pool(FixedSource([10.0, 10.0]), FixedSource([-20.0]), FixedSource([]))) == [
        50.0,
        math.inf,
    ]


@pytest.mark.asyncio
async def test_supports_pandas_backed_sources():
    # DummyTimeseriesSource emits 0, 10, 20 as a pandas frame; a pool only consuming has no production to match
    cluster = pool(DummyTimeseriesSource(), pool(DummyTimeseriesSource()))

    result = await AccSimultaneitySource(cluster).fetch_timeseries(
        START, START + dt.timedelta(hours=3), dt.timedelta(hours=1)
    )

    assert [row["value"] for row in result.to_arr()] == [100.0, math.inf, math.inf]


@pytest.mark.asyncio
async def test_no_volume_at_all_is_balanced():
    assert await fetch_values(pool(FixedSource([0.0]), FixedSource([0.0]))) == [100.0]


@pytest.mark.asyncio
async def test_metadata_has_unit_and_earliest_expiry():
    early = dt.datetime(2026, 1, 1, 1, tzinfo=dt.UTC)
    late = dt.datetime(2026, 1, 1, 2, tzinfo=dt.UTC)
    cluster = pool(
        FixedSource([10.0], metadata={"expires": late}), pool(FixedSource([-10.0], metadata={"expires": early}))
    )

    result = await AccSimultaneitySource(cluster).fetch_timeseries(START, START + QUARTER, QUARTER)

    assert result.metadata == {"unit": "%", "expires": early}


def test_resolutions_and_max_age_combine_all_nested_sources():
    minute = dt.timedelta(minutes=1)
    source = AccSimultaneitySource(
        pool(
            FixedSource([], resolutions=["PT15M", "PT1H"], max_age=dt.timedelta(hours=1)),
            pool(FixedSource([], resolutions=["PT15M"], max_age=minute)),
        )
    )

    assert source.supported_resolutions == ["PT15M"]
    assert source.max_age == minute


def test_member_is_either_a_source_or_a_cluster():
    with pytest.raises(ValueError):
        AccPoolMember()
    with pytest.raises(ValueError):
        AccPoolMember(source=FixedSource([]), cluster=pool(FixedSource([])))


def test_create_from_settings():
    source = TimeseriesSource.create(
        {
            "type": "acc_simultaneity",
            "cluster": {
                "type": "pool",
                "members": [
                    {"source": {"type": "dummy_timeseries_source"}},
                    {
                        "cluster": {
                            "type": "producer_share",
                            "members": [
                                {"source": {"type": "dummy_timeseries_source"}, "role": "producer", "share_ratio": 0.5}
                            ],
                        }
                    },
                ],
            },
        }
    )

    assert isinstance(source, AccSimultaneitySource)
    assert isinstance(source.cluster, AccPoolCluster)
    nested = source.cluster.members[1].cluster
    assert isinstance(nested, AccProducerShareCluster)
    assert isinstance(nested.members[0], AccShareMember)
    assert (nested.members[0].role, nested.members[0].share_ratio) == ("producer", 0.5)
    assert all(isinstance(s, DummyTimeseriesSource) for s in source.sources)


@pytest.mark.parametrize(
    "cluster",
    [
        {"type": "pool", "members": []},
        {"type": "pool", "members": [{}]},
        {
            "type": "pool",
            "members": [
                {
                    "source": {"type": "dummy_timeseries_source"},
                    "cluster": {"type": "pool", "members": [{"source": {"type": "dummy_timeseries_source"}}]},
                }
            ],
        },
        # ACC doesn't support nesting in a producer share cluster
        {
            "type": "producer_share",
            "members": [{"cluster": {"type": "pool", "members": [{"source": {"type": "dummy_timeseries_source"}}]}}],
        },
        {"type": "producer_share", "members": [{"source": {"type": "dummy_timeseries_source"}, "share_ratio": 1.5}]},
        {
            "type": "capacity_priority",
            "members": [{"source": {"type": "dummy_timeseries_source"}, "consumption_capacity_kwh": -1}],
        },
        {"type": "producer_priority", "members": [{"source": {"type": "dummy_timeseries_source"}, "role": "both"}]},
        {"type": "acc_cluster"},
    ],
)
def test_rejects_invalid_settings(cluster: dict):
    with pytest.raises(ValidationError):
        TimeseriesSource.create({"type": "acc_simultaneity", "cluster": cluster})
