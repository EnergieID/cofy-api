from typing import Literal

from cofy.modules.timeseries import NumericSource, NumericSourceSettings


class NetVolumeSourceSettings(NumericSourceSettings):
    type: Literal["net_volume_source"] = "net_volume_source"


class NetVolumeSource(NumericSource, settings=NetVolumeSourceSettings, abstract=True):
    """A source of net volumes in kWh, positive for consumption and negative for production."""


class RatioSourceSettings(NumericSourceSettings):
    type: Literal["ratio_source"] = "ratio_source"


class RatioSource(NumericSource, settings=RatioSourceSettings, abstract=True):
    """A source of ratios, as percentages."""
