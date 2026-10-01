from abc import ABC
from typing import Literal

from cofy.modules.timeseries import TimeseriesFormat, TimeseriesFormatSettings


class PriceFormatSettings(TimeseriesFormatSettings):
    type: Literal["price_format"] = "price_format"


class PriceFormat(TimeseriesFormat, ABC, settings=PriceFormatSettings, abstract=True):
    """A format that only fits prices."""
