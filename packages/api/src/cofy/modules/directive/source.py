from typing import Literal

from cofy.modules.timeseries import TimeseriesSource, TimeseriesSourceSettings


class DirectiveSeriesSourceSettings(TimeseriesSourceSettings):
    type: Literal["directive_series_source"] = "directive_series_source"


class DirectiveSeriesSource(TimeseriesSource, settings=DirectiveSeriesSourceSettings, abstract=True):
    """A source of directive steps."""


class BoundarySourceSettings(TimeseriesSourceSettings):
    type: Literal["boundary_source"] = "boundary_source"


class BoundarySource(TimeseriesSource, settings=BoundarySourceSettings, abstract=True):
    """A source of directive boundaries, in four ascending columns `b0` to `b3` per timestamp."""
