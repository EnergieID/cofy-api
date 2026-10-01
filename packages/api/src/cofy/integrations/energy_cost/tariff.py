from typing import Literal

from pydantic import Field

from cofy.api import Resource, ResourceSettings
from energy_cost import Tariff


class TariffResourceSettings(ResourceSettings):
    type: Literal["tariff"] = "tariff"
    value: Tariff = Field(description="Energy cost tariff instance")


class TariffResource(Resource, settings=TariffResourceSettings):
    """An energy cost tariff."""
