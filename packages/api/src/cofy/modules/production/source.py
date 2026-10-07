from typing import Literal

from cofy.modules.timeseries import NumericSource, NumericSourceSettings


class ProductionSourceSettings(NumericSourceSettings):
    type: Literal["production_source"] = "production_source"


class ProductionSource(NumericSource, settings=ProductionSourceSettings, abstract=True):
    """A source of produced energy, positive in kWh."""
