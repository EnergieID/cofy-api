from abc import ABC
from typing import Literal

from cofy.modules.timeseries import TimeseriesFormat, TimeseriesFormatSettings


class DirectiveSeriesFormatSettings(TimeseriesFormatSettings):
    type: Literal["directive_series_format"] = "directive_series_format"


class DirectiveSeriesFormat(TimeseriesFormat, ABC, settings=DirectiveSeriesFormatSettings, abstract=True):
    """A format that only fits directive steps."""
