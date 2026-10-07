from typing import TYPE_CHECKING, Literal

from cofy.api import Resource, ResourceSettings

from .source import TimeseriesSourceSettings

if TYPE_CHECKING:
    # Published at runtime by finalize(); the base class is the static stand-in.
    AnyTimeseriesSourceSettings = TimeseriesSourceSettings


class SourceResourceSettings(ResourceSettings):
    type: Literal["source"] = "source"
    # Unresolved until cofy.api.finalize() publishes the discriminated unions.
    value: "AnyTimeseriesSourceSettings"


class SourceResource(Resource, settings=SourceResourceSettings):
    """A timeseries source, built once and shared by every reference to it."""
