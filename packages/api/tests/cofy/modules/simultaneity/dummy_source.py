from typing import Literal

from cofy.modules.simultaneity import NetVolumeSource, NetVolumeSourceSettings
from tests.cofy.modules.timeseries.dummy_source import DummyTimeseriesSource


class DummyNetVolumeSourceSettings(NetVolumeSourceSettings):
    type: Literal["dummy_net_volume_source"] = "dummy_net_volume_source"


class DummyNetVolumeSource(DummyTimeseriesSource, NetVolumeSource, settings=DummyNetVolumeSourceSettings):
    """The dummy source, as a source of net volumes."""
