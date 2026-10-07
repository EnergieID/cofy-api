from typing import Literal

from cofy.modules.timeseries import NumericSource, NumericSourceSettings


class PriceSourceSettings(NumericSourceSettings):
    type: Literal["price_source"] = "price_source"


class PriceSource(NumericSource, settings=PriceSourceSettings, abstract=True):
    """A source of prices."""
