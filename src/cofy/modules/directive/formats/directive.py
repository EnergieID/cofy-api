from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from cofy.modules.timeseries import JSONFormat

DirectiveSteps = Literal["--", "-", "0", "+", "++"]
DIRECTIVE_STEPS = DirectiveSteps.__args__


class DirectiveRecord(BaseModel):
    timestamp: datetime
    value: DirectiveSteps


class DirectiveFormat[MetadataType: BaseModel](JSONFormat[DirectiveRecord, MetadataType]):
    def __init__(self, MT: type[MetadataType] | None = None):
        super().__init__(DT=DirectiveRecord, MT=MT)
