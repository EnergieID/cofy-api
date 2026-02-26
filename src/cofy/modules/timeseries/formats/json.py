import datetime as dt

from pydantic import BaseModel

from cofy.modules.timeseries.format import TimeseriesFormat
from cofy.modules.timeseries.model import Timeseries


class DefaultDataType(BaseModel):
    timestamp: dt.datetime
    value: float


class DefaultMetadataType(BaseModel):
    start: dt.datetime | None = None
    end: dt.datetime | None = None
    format: str = "json"
    resolution: dt.timedelta | None = None


class ResponseModel[DataType: BaseModel, MetadataType: BaseModel](BaseModel):
    metadata: MetadataType
    data: list[DataType]


class JSONFormat[DataType: BaseModel, MetadataType: BaseModel](TimeseriesFormat):
    """Timeseries format for JSON."""

    name = "json"

    # We need to pass the typing info at runtime, otherwise we don't have enough info to create the openapi schema
    # root cause is type erasure, see https://github.com/python/typing/issues/629#issuecomment-1831106590
    def __init__(self, DT: type[DataType] | None = None, MT: type[MetadataType] | None = None):
        super().__init__()
        self.DT = DT or DefaultDataType
        self.MT = MT or DefaultMetadataType
        self.ResponseModel = ResponseModel[self.DT, self.MT]

    def format(self, timeseries: Timeseries) -> ResponseModel:
        return self.ResponseModel(
            metadata=self.MT(**timeseries.metadata),
            data=[self.DT(**row) for row in timeseries.to_arr()],
        )

    @property
    def ReturnType(self) -> type:
        return self.ResponseModel
