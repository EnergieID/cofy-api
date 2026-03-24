from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from cofy.modules.timeseries import JSONFormat

DIRECTIVE_STEPS = ("--", "-", "0", "+", "++")


class DirectiveSteps(StrEnum):
    NEGATIVE = "--"
    SLIGHT_NEGATIVE = "-"
    NEUTRAL = "0"
    SLIGHT_POSITIVE = "+"
    POSITIVE = "++"


class DirectiveRecord(BaseModel):
    timestamp: datetime
    value: DirectiveSteps


class DirectiveFormat[MetadataType: BaseModel](JSONFormat[DirectiveRecord, MetadataType]):
    def __init__(self, MT: type[MetadataType] | None = None):
        super().__init__(DT=DirectiveRecord, MT=MT)
