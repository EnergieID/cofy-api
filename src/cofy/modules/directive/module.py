from cofy.modules.timeseries import (
    TimeseriesFormat,
    TimeseriesModule,
    TimeseriesModuleSettings,
    TimeseriesSource,
)

from .formats.directive import DirectiveFormat


class DirectiveModuleSettings(TimeseriesModuleSettings):
    type: str = "directive"


class DirectiveModule(TimeseriesModule, settings=DirectiveModuleSettings):
    type: str = "directive"
    type_description: str = "Module providing directives as time series."

    def __init__(self, source: TimeseriesSource, formats: list[TimeseriesFormat] | None = None, **kwargs):
        if formats is None:
            formats = [DirectiveFormat()]

        super().__init__(source=source, formats=formats, **kwargs)
