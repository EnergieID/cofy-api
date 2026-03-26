from cofy.modules.timeseries import TimeseriesFormat, TimeseriesModule, TimeseriesSource

from .formats.directive import DirectiveFormat


class DirectiveModule(TimeseriesModule):
    type: str = "directive"
    type_description: str = "Module providing directives as time series."

    def __init__(self, source: TimeseriesSource, formats: list[TimeseriesFormat] | None = None, **kwargs):
        if formats is None:
            formats = [DirectiveFormat()]

        super().__init__(source=source, formats=formats, **kwargs)
